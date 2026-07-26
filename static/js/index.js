import { apiGet } from "./common.js";

export async function loadDecks() {
  const deckList = document.getElementById("deck-list");

  const response = await apiGet(`decks`);
  if (response.ok !== true) {
    deckList.innerHTML = `<p>Loading error: ${data.message || ""}</p>`;
    return;
  }
  const decks = response.data || [];
  if (decks.length === 0) {
    deckList.innerHTML = "<p>No decks available.</p>";
    return;
  }
  deckList.innerHTML = "";
  decks.forEach((deck) => {
    const deckDiv = document.createElement("div");
    deckDiv.innerHTML = `<a href="/deck/${deck.id}">${deck.name}</a>`;
    deckList.appendChild(deckDiv);
  });
}
