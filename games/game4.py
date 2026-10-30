# 구간 맞히기 (중) 확률: ⅓ (3배)

import streamlit as st
from modules.ui_components import show_placeholder_page

# 정의된 함수: show_game4

def show_game_4(): show_placeholder_page("게임 4")


<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>기사 일치율 배팅 게임</title>
<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 25px 15px;
  background: #111827;
  color: white;
  font-family: Arial, sans-serif;
}

.container {
  max-width: 750px;
  margin: auto;
}

h1 {
  text-align: center;
  color: #facc15;
}

.card {
  background: #1f2937;
  border-radius: 15px;
  padding: 22px;
  margin: 18px 0;
}

h2 { color: #facc15; }

input, textarea {
  width: 100%;
  padding: 12px;
  margin: 8px 0 15px;
  border: 1px solid #4b5563;
  border-radius: 8px;
  background: #374151;
  color: white;
  font-size: 16px;
}

textarea {
  min-height: 130px;
  resize: vertical;
}

button {
  padding: 13px 18px;
  border: none;
  border-radius: 9px;
  background: #eab308;
  color: #111827;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
}

button:hover { background: #facc15; }

.score {
  text-align: center;
  font-size: 25px;
  color: #4ade80;
  font-weight: bold;
}

.range-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.range {
  padding: 20px 5px;
  background: #374151;
  border: 2px solid transparent;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  font-size: 17px;
  font-weight: bold;
}

.range.selected {
  border-color: #facc15;
  background: #713f12;
}

.range input { display: none; }

.result {
  text-align: center;
  font-size: 23px;
  font-weight: bold;
  margin-top: 20px;
}

.small {
  color: #9ca3af;
  font-size: 13px;
}

.article-title {
  font-size: 23px;
  font-weight: bold;
  line-height: 1.5;
}

#game { display: none; }

@media(max-width: 450px) {
  .range { font-size: 14px; }
}
</style>
</head>

<body>
<div class="container">

<h1>🎯 기사 일치율 배팅 게임</h1>

<div class="card">
  <h2>💰 나의 보유 점수</h2>
  <div class="score" id="balance">1,000점</div>
</div>

<!-- 기사 입력 -->
<div class="card" id="admin">
  <h2>📝 기사 설정</h2>

  <label>기사 제목</label>
  <input id="articleTitle" placeholder="기사 제목을 입력하세요">

  <label>기사 본문</label>
  <textarea id="articleBody" placeholder="기사 본문을 입력하세요"></textarea>

  <label>정답 일치율 (1~100)</label>
  <input id="correctAnswer" type="number" min="1" max="100"
         placeholder="관리자만 아는 정답을 입력하세요">

  <button onclick="startGame()">게임 시작</button>
  <p class="small">※ 정답은 게임 중 공개되지 않습니다.</p>
</div>

<!-- 게임 화면 -->
<div id="game">

  <div class="card">
    <h2>📰 오늘의 기사</h2>
    <div class="article-title" id="showTitle"></div>
    <hr>
    <p id="showBody" style="line-height:1.8; white-space:pre-wrap;"></p>
  </div>

  <div class="card">
    <h2>🎯 예상 일치율을 선택하세요</h2>
    <p class="small">제목과 본문의 일치율은 어느 구간일까요?</p>

    <div class="range-list">
      <label class="range">
        <input type="radio" name="range" value="1">
        1~33%
      </label>

      <label class="range">
        <input type="radio" name="range" value="2">
        34~66%
      </label>

      <label class="range">
        <input type="radio" name="range" value="3">
        67~100%
      </label>
    </div>
  </div>

  <div class="card">
    <h2>💸 배팅 점수</h2>
    <input id="bet" type="number" min="1"
           placeholder="배팅할 점수를 입력하세요">

    <p class="small">
      정답: 배팅 점수의 3배 지급<br>
      오답: 배팅 점수 전액 차감
    </p>

    <button id="betButton" onclick="playGame()" style="width:100%">
      배팅하기
    </button>

    <div class="result" id="result"></div>
  </div>

  <button onclick="newRound()" style="width:100%">
    다음 기사 설정하기
  </button>

</div>
</div>

<script>
let balance = 1000;
let answer = 0;
let played = false;

function updateBalance() {
  document.getElementById("balance").textContent =
    balance.toLocaleString() + "점";
}

function startGame() {
  const title = document.getElementById("articleTitle").value.trim();
  const body = document.getElementById("articleBody").value.trim();
  const correct = Number(document.getElementById("correctAnswer").value);

  if (!title || !body) {
    alert("기사 제목과 본문을 입력해주세요.");
    return;
  }

  if (!Number.isInteger(correct) || correct < 1 || correct > 100) {
    alert("정답 일치율을 1~100 사이의 정수로 입력해주세요.");
    return;
  }

  answer = correct;

  document.getElementById("showTitle").textContent = title;
  document.getElementById("showBody").textContent = body;

  document.getElementById("admin").style.display = "none";
  document.getElementById("game").style.display = "block";
  document.getElementById("result").textContent = "";

  played = false;
  document.getElementById("betButton").disabled = false;
  document.getElementById("betButton").textContent = "배팅하기";

  document.querySelectorAll('input[name="range"]').forEach(r => {
    r.checked = false;
    r.parentElement.classList.remove("selected");
  });

  document.getElementById("bet").value = "";
}

document.querySelectorAll('input[name="range"]').forEach(radio => {
  radio.addEventListener("change", function() {
    document.querySelectorAll(".range").forEach(el => {
      el.classList.remove("selected");
    });
    this.parentElement.classList.add("selected");
  });
});

function playGame() {
  if (played) return;

  const selected = document.querySelector(
    'input[name="range"]:checked'
  );

  const bet = Number(document.getElementById("bet").value);

  if (!selected) {
    alert("일치율 구간을 선택해주세요.");
    return;
  }

  if (!Number.isInteger(bet) || bet < 1 || bet > balance) {
    alert("보유 점수 내에서 배팅 점수를 입력해주세요.");
    return;
  }

  const range = Number(selected.value);

  let correctRange;

  if (answer <= 33) {
    correctRange = 1;
  } else if (answer <= 66) {
    correctRange = 2;
  } else {
    correctRange = 3;
  }

  played = true;

  if (range === correctRange) {
    balance = balance - bet + (bet * 3);

    document.getElementById("result").innerHTML =
      "🎉 정답입니다!<br>" +
      "실제 일치율: " + answer + "%<br>" +
      "+" + (bet * 3).toLocaleString() + "점 지급!";
  } else {
    balance -= bet;

    document.getElementById("result").innerHTML =
      "❌ 틀렸습니다!<br>" +
      "실제 일치율: " + answer + "%<br>" +
      "-" + bet.toLocaleString() + "점";
  }

  updateBalance();

  document.getElementById("betButton").disabled = true;
  document.getElementById("betButton").textContent = "배팅 완료";
}

function newRound() {
  document.getElementById("game").style.display = "none";
  document.getElementById("admin").style.display = "block";

  document.getElementById("articleTitle").value = "";
  document.getElementById("articleBody").value = "";
  document.getElementById("correctAnswer").value = "";
}

updateBalance();
</script>
</body>
</html>

