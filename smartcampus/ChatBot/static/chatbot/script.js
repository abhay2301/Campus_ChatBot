function sendMessage() {
  const input = document.getElementById("userInput");
  const message = input.value;

  fetch("/chat/", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: `message=${encodeURIComponent(message)}`
  })
  .then(response => response.json())
  .then(data => {
    const chatBox = document.getElementById("chat-box");
    chatBox.innerHTML += `<p><strong>You:</strong> ${message}</p>`;
    chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
    input.value = "";
  });
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
