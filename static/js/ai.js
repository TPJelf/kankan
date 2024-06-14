import { GoogleGenerativeAI } from 'https://esm.run/@google/generative-ai';

async function run_ai(API_KEY, parent_name, parent_pk, subtasks) {
  const genAI = new GoogleGenerativeAI(API_KEY);
  const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });

  const prompt =
    'Hi. This request is for a todo app. Please provide 5 new subtasks for this task: ' +
    parent_name +
    ". Your reply must only contain the subtasks in a json array. Please provide tasks that can be completed without specifying equipement, for example clean floors instead of vacuum floors. Also avoid subtasks that refer to children or pets. Here's a list of all the subtasks already created, please avoid repeating them:" +
    subtasks +
    '. Thank you very much!';

  const result = await model.generateContent(prompt);
  const response = await result.response;
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const task_names = response.text();
  const fetch_url = '/create_ai_tasks/' + parent_pk + '/';

  const payload = await fetch(fetch_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
    },
    body: task_names,
  });

  if (payload.ok) {
    htmx.ajax('GET', window.location.href, {
      target: 'body',
      source: document.getElementById('button-ai'),
    });
  } else {
    error_toast('AI FAIL. ALL IS LOST.');
    document.getElementById('main-spinner').style.opacity = 0;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  activate_ai();
});

document.addEventListener('htmx:afterSwap', () => {
  activate_ai();
});

function activate_ai() {
  var button_ai = document.getElementById('button-ai');
  if (button_ai) {
    button_ai.addEventListener('click', () => {
      document.getElementById('main-spinner').style.opacity = 1;
      run_ai(API_KEY, parent_name, parent_pk, subtasks);
    });
  }
}
