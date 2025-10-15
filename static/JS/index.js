function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}
function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}
function switchModal(openId, closeId) {
  closeModal(closeId);
  openModal(openId);
}

function copyToClipboard() {
  const input = document.getElementById("short-url");
  input.select();
  navigator.clipboard.writeText(input.value);
  alert("Copied to clipboard!");
}
