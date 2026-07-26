import { apiGet, apiPost } from "./common.js";

let state = {
  currentCard: null,
  revealed: false,
};

const app = document.getElementById("app");
const modeLabel = document.getElementById("mode-label");

export async function loadNext(deckId) {
  state.revealed = false;

  const response = await apiGet(`deck/${deckId}/cards/next`);
  if (response.ok !== true) {
    app.innerHTML = `<p>Loading error: ${data.message || ""}</p>`;
    return;
  }
  const deck = response.data.deck;
  const card = response.data.card;

  const deckName = deck.name || "Deck";
  modeLabel.innerHTML = `<h3>${deckName}</h3>`;

  if (card) {
    state.currentCard = card;
    renderCard(deckId);
  } else {
    renderDone(deckId);
  }
}

async function review(cardId, result, deckId) {
  const response = await apiPost(`cards/${cardId}/review?result=${result}`);
  if (response.ok !== true) {
    alert("Error: " + (response.message || "Failed to submit review"));
    return;
  }
  await loadNext(deckId);
}

async function resetProgress(deckId) {
  const response = await apiPost(`deck/${deckId}/reset`);
  if (response.ok !== true) {
    alert("Error: " + (response.message || "Failed to reset progress"));
    return;
  }
  await loadNext(deckId);
}

function toggleReveal(deckId) {
  state.revealed = !state.revealed;
  renderCard(deckId);
}

function renderCard(deckId) {
  const card = state.currentCard;
  const text = state.revealed ? card.back : card.front;

  app.innerHTML = `
    <p>${text}</p>
    <button id="btn-toggle">Show ${state.revealed ? "Front" : "Back"}</button>
    <button id="btn-revise">Revise</button>
    <button id="btn-know">Know</button>
  `;

  document.getElementById("btn-toggle").addEventListener("click", () => toggleReveal(deckId));
  document
    .getElementById("btn-revise")
    .addEventListener("click", () => review(card.id, "revise", deckId));
  document
    .getElementById("btn-know")
    .addEventListener("click", () => review(card.id, "know", deckId));
}

function renderDone(deckId) {
  app.innerHTML = `
    <p>You have completed all cards in this deck!</p>
    <button id="btn-reset">Start over</button>
  `;

  document.getElementById("btn-reset").addEventListener("click", () => resetProgress(deckId));
}
