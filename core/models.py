from datetime import timedelta
from random import choice

from django.contrib.auth.models import User
from django.db import connection, models, transaction
from django.utils import timezone


# Create your models here.
class Settings(models.Model):
    """
    User settings.

    # TODO: Locale.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="settings")
    ai_apikey = models.CharField(max_length=255, null=True, blank=True)


class Task(models.Model):
    """
    Represents a task that can be assigned to a user. Tasks can be nested to create
    subtasks.

    TODO: UUID to avoid exposing ids in frontend.
    TODO: Proper permissions.
    """

    class Status(models.IntegerChoices):
        PENDING = 1, "Pending"
        INPROGRESS = 2, "In progress"
        DONE = 3, "Done"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    position = models.IntegerField(default=1)
    parent = models.ForeignKey(
        "self", null=True, default=None, on_delete=models.CASCADE
    )
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["id"]),
            models.Index(fields=["parent_id"]),
            models.Index(fields=["updated_on"]),
        ]

    def __str__(self):
        return self.name

    def count_recently_updated_subtasks(self):
        now = timezone.now()
        last_24_hours = now - timedelta(hours=24)
        last_7_days = now - timedelta(days=7)

        query = """
        WITH RECURSIVE task_tree AS (
            SELECT id
            FROM core_task
            WHERE id = %s
            UNION ALL
            SELECT t.id
            FROM core_task t
            JOIN task_tree tt ON t.parent_id = tt.id
        )
        SELECT
            SUM(CASE WHEN updated_on >= %s AND updated_on < %s THEN 1 ELSE 0 END) AS count_last_24_hours,
            SUM(CASE WHEN updated_on >= %s AND updated_on < %s THEN 1 ELSE 0 END) AS count_last_7_days
            
        FROM core_task
        WHERE id IN (SELECT id FROM task_tree)
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [self.pk, last_24_hours, now, last_7_days, now])
            result = cursor.fetchone()

        return {
            "count_last_24_hours": result[0],
            "count_last_7_days": result[1],
        }

    def random_unfinished_base_task(self):
        """
        Returns a random unfinished base task for the given user. A base task is a task that
        does not have any subtasks. Only tasks with status 'To do' or 'In progress' are considered.

                Returns:
        Task: A random unfinished base task, or None if no such task exists.
        """

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE task_tree AS (
                    SELECT id, name, status, parent_id
                    FROM core_task
                    WHERE id = %s
                    UNION ALL
                    SELECT t.id, t.name, t.status, t.parent_id
                    FROM core_task t
                    INNER JOIN task_tree tt ON t.parent_id = tt.id
                )
                SELECT id, name, status, parent_id
                FROM task_tree
                WHERE id NOT IN (SELECT parent_id FROM core_task WHERE parent_id IS NOT NULL)
                AND status IN (1, 2)
            """,
                [self.pk],
            )
            rows = cursor.fetchall()

        tasks = [
            Task(id=row[0], name=row[1], status=row[2], parent_id=row[3])
            for row in rows
        ]

        if tasks:
            return choice(tasks)
        else:
            return None

    def supertask(self):
        """
        Returns the top-level task in the hierarchy to which this task belongs.

        Returns:
        Task: The top-level task in the hierarchy.
        """
        task = self
        while task.parent:
            task = task.parent
        return task

    def breadcrumbs(self):
        """
        Returns the list of tasks from the top-level task to this task, representing the
        hierarchy path.

        Returns:
        list: A list of tasks from the top-level task to this task.
        """
        breadcrumbs = []
        task = self

        while task:
            breadcrumbs.insert(0, task)
            task = task.parent

        return breadcrumbs

    def reset(self):
        self.status = self.Status.PENDING
        self.save()

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Saves the task to the database.
        Updates positions of other tasks if the position or status of this task changes.
        Propagates status changes up and down. # TODO: Better up and down propagation
        """

        if self.pk is not None:  # if self exists
            original = Task.objects.get(pk=self.pk)

            if original.status != self.status:

                Task.objects.filter(
                    parent=self.parent,
                    status=self.status,
                    position__gte=self.position,
                    user=self.user,
                ).update(position=models.F("position") + 1)

                Task.objects.filter(
                    parent=self.parent,
                    status=original.status,
                    position__gt=original.position,
                    user=self.user,
                ).update(position=models.F("position") - 1)

                parent = self.parent

                if self.status == self.Status.DONE:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            WITH RECURSIVE task_tree AS (
                                SELECT id FROM core_task WHERE id = %s
                                UNION ALL
                                SELECT t.id FROM core_task t
                                INNER JOIN task_tree tt ON t.parent_id = tt.id
                            )
                            UPDATE core_task SET status = 3 WHERE id IN (SELECT id FROM task_tree);
                            """,
                            [self.pk],
                        )

                    if parent and parent.parent:
                        subtasks = Task.objects.filter(parent=parent)
                        if all(
                            subtask.status == self.Status.DONE for subtask in subtasks
                        ):
                            parent.status = self.Status.DONE
                            parent.save()

                elif self.status == self.Status.PENDING:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            WITH RECURSIVE task_tree AS (
                                SELECT id FROM core_task WHERE id = %s
                                UNION ALL
                                SELECT t.id FROM core_task t
                                INNER JOIN task_tree tt ON t.parent_id = tt.id
                            )
                            UPDATE core_task SET status = 1 WHERE id IN (SELECT id FROM task_tree);
                            """,
                            [self.pk],
                        )

                    if parent and parent.parent and parent.status == self.Status.DONE:
                        parent.status = Task.Status.INPROGRESS
                        parent.save()

                elif self.status == self.Status.INPROGRESS:
                    if parent and parent.parent:
                        parent.status = Task.Status.INPROGRESS
                        parent.save()

            else:
                if original.position > self.position:
                    Task.objects.filter(
                        parent=self.parent,
                        status=self.status,
                        position__gte=self.position,
                        position__lt=original.position,
                        user=self.user,
                    ).update(position=models.F("position") + 1)
                else:
                    Task.objects.filter(
                        parent=self.parent,
                        status=self.status,
                        position__lte=self.position,
                        position__gt=original.position,
                        user=self.user,
                    ).update(position=models.F("position") - 1)

        else:  # Add to bottom of home
            max_position = Task.objects.filter(
                status=self.status, user=self.user, parent=self.parent
            ).aggregate(models.Max("position"))["position__max"]
            self.position = max_position + 1 if max_position is not None else 1

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Deletes the task from the database. Updates the positions of other tasks with the
        same parent and status.
        """

        Task.objects.filter(
            parent=self.parent,
            status=self.status,
            position__gt=self.position,
        ).update(position=models.F("position") - 1)

        super().delete(*args, **kwargs)
