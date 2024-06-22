var sortablejs_options = {
  group: 'tasks',
  draggable: '.task',
  animation: 150,
  handle: '.handle',
  swapThreshold: 0.8,

  onEnd: (event) => {
    let task = event.item;
    const new_task_position =
      Array.from(task.parentNode.children).indexOf(task) + 1;
    const new_task_status = event.to.parentNode.id.split('-')[1];

    // Cancel move is the task lands outside a status
    if (!event.to.classList.contains('status-body')) {
      event.from.insertBefore(event.item, event.from.children[event.oldIndex]);
    } else {
      new_url =
        '/update_task_position/' +
        task.id +
        '/' +
        new_task_status +
        '/' +
        new_task_position +
        '/';

      task.removeAttribute('hx-post');
      task.setAttribute('hx-post', new_url);
      htmx.process(task);

      task = event.item;
      last_update = document.getElementById('last-update');

      var current_date = new Date();
      var formatted_date = current_date.toISOString().split('T')[0];
      last_update.innerHTML = formatted_date;
      htmx.trigger(task, 'update_task_position');
      if (new_task_status == 3 && event.from.parentNode.id.split('-')[1] != 3) {
        shoot_confetti();
      }
    }
  },
};

function activate_stuff() {
  document.querySelectorAll('.status-body').forEach((status) => {
    new Sortable(status, sortablejs_options);
  });

  // Previous link url update
  var previous_link = document.getElementById('previous-link');
  if (previous_link && sessionStorage.getItem('previous_url')) {
    previous_link.setAttribute('href', sessionStorage.getItem('previous_url'));
  }

  // Dice animation
  var dice_button = document.getElementById('dice-button');
  if (dice_button) {
    dice_button.addEventListener('click', () => {
      const dice = document.getElementById('dice');
      dice.classList.remove('roll');
      void dice.offsetWidth;
      dice.classList.add('roll');
    });
  }

  //Search button update
  var search_button = document.getElementById('search-button');
  var search_term = document.getElementById('search-term');
  if (search_term) {
    search_term.addEventListener('input', function () {
      const input = this.value;
      const options = document.querySelectorAll('#search-task-list option');
      let dataValue = null;

      options.forEach((option) => {
        if (option.value === input) {
          dataValue = option.getAttribute('task-id');
        }
      });

      if (dataValue !== null) {
        if (dataValue == '0') {
          search_button.setAttribute('hx-get', '/home/');
        } else {
          search_button.setAttribute('hx-get', '/task/' + dataValue);
        }
        htmx.process(search_button);
      } else {
        search_button.removeAttribute('hx-get');
        htmx.process(search_button);
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  activate_stuff();
});

document.addEventListener('htmx:afterSwap', () => {
  activate_stuff();
});

// Hack for datalist search proper functioning
function checkUserKeydown(event) {
  return event instanceof KeyboardEvent;
}

// HTMX CSS Transitions
htmx.config.globalViewTransitions = true;

// Toggles card sizes except when text is selected.
document.querySelectorAll('.card-expandable').forEach((card) => {
  card.addEventListener('click', (event) => {
    if (event.target.classList.contains('card-expandable-toggler')) {
      if (!window.getSelection().toString()) {
        card.classList.toggle('expanded');
      }
    }
    if (event.target.classList.contains('dropdown-toggle')) {
      if (event.target.nextElementSibling.classList.contains('show')) {
        card.classList.add('expanded');
      } else {
        card.classList.remove('expanded');
      }
    }
  });
});

// Deselect text after click to enable card size toggling.
document.addEventListener('click', (event) => {
  if (
    !event.target.classList.contains('task-name') &&
    !(event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA')
  ) {
    window.getSelection().removeAllRanges();
  }
});

// Prevents space name submissions. Updates history for previous page link
document.addEventListener('htmx:beforeRequest', (event) => {
  var new_url = window.location.href;
  var previous_url = sessionStorage.getItem('previous_url');
  if (new_url != previous_url && !new_url.includes('/account/')) {
    sessionStorage.setItem('previous_url', window.location.href);
  }

  const form = event.detail.elt;
  const name_input = form.querySelector('#name');

  if (name_input && name_input.value.trim() === '') {
    name_input.value = '';
    name_input.reportValidity();
    event.preventDefault();
  }
});

// HTMX error handling goes here.
document.addEventListener('htmx:afterRequest', (event) => {
  if (!event.detail.successful) {
    // No pending tasks dice error reload hack
    if (event.detail.elt.id == 'dice-button') {
      htmx.ajax('GET', window.location.href, {
        target: 'body',
        source: event.detail.elt.parentNode,
      });
    } else {
      error_toast();
    }
  }
});

function error_toast(error_message = null) {
  const toast = new bootstrap.Toast(document.getElementById('error-toast'));
  document.getElementById('error-toast-message').textContent = error_message;
  toast.show();
}

// Cheer animation for when user completes tasks.
var defaults_confetti = {
  origin: { y: 1.2 },
};

function fire(particleRatio, opts) {
  confetti({
    ...defaults_confetti,
    ...opts,
    particleCount: Math.floor(200 * particleRatio),
  });
}

function shoot_confetti() {
  fire(0.25, {
    spread: 26,
    startVelocity: 85,
  });
  fire(0.2, {
    spread: 60,
    startVelocity: 75,
  });
  fire(0.35, {
    spread: 100,
    decay: 0.91,
    scalar: 0.8,
    startVelocity: 65,
  });
  fire(0.1, {
    spread: 120,
    startVelocity: 55,
    decay: 0.92,
    scalar: 1.2,
  });
  fire(0.1, {
    spread: 120,
    startVelocity: 45,
  });
}
