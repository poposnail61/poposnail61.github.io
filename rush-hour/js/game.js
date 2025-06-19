import {generatePuzzleByDifficulty, solvePuzzle, classifyDifficulty} from './puzzles.js';

const boardSize=6;
const cellSize=80;
const exitRow=2;
const exitWidth=20;
const boardPixelSize=boardSize*cellSize;
const canvas=document.getElementById('board');
canvas.width=boardPixelSize+exitWidth;
canvas.height=boardPixelSize;
const ctx=canvas.getContext('2d');
const startDiv=document.getElementById('start');
const dialog=document.getElementById('dialog');
const restartBtn=document.getElementById('restartBtn');

// Ensure start screen is visible and dialog hidden on initial load
startDiv.classList.remove('hidden');
dialog.classList.add('hidden');
canvas.classList.add('hidden');

let cars=[];
let selected=null;
let currentLevel=1;

function draw(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle='#000';
  for(let i=0;i<=boardSize;i++){
    ctx.beginPath();
    ctx.moveTo(i*cellSize,0);
    ctx.lineTo(i*cellSize,boardPixelSize);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0,i*cellSize);
    ctx.lineTo(boardPixelSize,i*cellSize);
    ctx.stroke();
  }
  ctx.fillStyle='green';
  ctx.fillRect(boardPixelSize,exitRow*cellSize+2,exitWidth,cellSize-4);
  for(const car of cars){
    ctx.fillStyle=car.color;
    const x=car.x*cellSize;
    const y=car.y*cellSize;
    const w=car.dir==='H'?car.length*cellSize:cellSize;
    const h=car.dir==='V'?car.length*cellSize:cellSize;
    ctx.fillRect(x+2,y+2,w-4,h-4);
  }
  ctx.fillStyle='#000';
  ctx.font='16px sans-serif';
  ctx.fillText('난이도 '+currentLevel,10,20);
}

function carAt(x,y){
  return cars.find(c=>{
    for(let i=0;i<c.length;i++){
      const cx=c.dir==='H'?c.x+i:c.x;
      const cy=c.dir==='V'?c.y+i:c.y;
      if(cx===x&&cy===y)return true;
    }
    return false;
  });
}

function isFree(x,y,ignore){
  for(const c of cars){
    if(c===ignore)continue;
    for(let i=0;i<c.length;i++){
      const cx=c.dir==='H'?c.x+i:c.x;
      const cy=c.dir==='V'?c.y+i:c.y;
      if(cx===x&&cy===y)return false;
    }
  }
  return x>=0&&x<boardSize&&y>=0&&y<boardSize;
}

function tryMove(car,newX,newY){
  if(car.dir==='H'){if(newY!==car.y)return;for(let i=0;i<car.length;i++)if(!isFree(newX+i,newY,car))return;car.x=newX;}
  else{if(newX!==car.x)return;for(let i=0;i<car.length;i++)if(!isFree(newX,newY+i,car))return;car.y=newY;}
  if(car.red&&car.x+car.length===boardSize&&car.y===exitRow)setTimeout(()=>{dialog.classList.remove('hidden');},50);
}

canvas.addEventListener('mousedown',e=>{
  const rect=canvas.getBoundingClientRect();
  const x=Math.floor((e.clientX-rect.left)/cellSize);
  const y=Math.floor((e.clientY-rect.top)/cellSize);
  const car=carAt(x,y);
  if(car)selected={car,ox:car.x,oy:car.y,sx:e.clientX,sy:e.clientY};
});

canvas.addEventListener('touchstart',e=>{
  const t=e.touches[0];
  const rect=canvas.getBoundingClientRect();
  const x=Math.floor((t.clientX-rect.left)/cellSize);
  const y=Math.floor((t.clientY-rect.top)/cellSize);
  const car=carAt(x,y);
  if(car)selected={car,ox:car.x,oy:car.y,sx:t.clientX,sy:t.clientY};
  e.preventDefault();
},{passive:false});

window.addEventListener('mousemove',e=>{
  if(!selected)return;
  const car=selected.car;
  const dx=Math.round((e.clientX-selected.sx)/cellSize);
  const dy=Math.round((e.clientY-selected.sy)/cellSize);
  if(car.dir==='H')tryMove(car,selected.ox+dx,car.y);
  else tryMove(car,car.x,selected.oy+dy);
  draw();
});

window.addEventListener('touchmove',e=>{
  if(!selected)return;
  const t=e.touches[0];
  const car=selected.car;
  const dx=Math.round((t.clientX-selected.sx)/cellSize);
  const dy=Math.round((t.clientY-selected.sy)/cellSize);
  if(car.dir==='H')tryMove(car,selected.ox+dx,car.y);
  else tryMove(car,car.x,selected.oy+dy);
  draw();
  e.preventDefault();
},{passive:false});

window.addEventListener('mouseup',()=>{selected=null;});
window.addEventListener('touchend',()=>{selected=null;},{passive:false});

function startGame(level){
  const puzzle=generatePuzzleByDifficulty(level);
  if(!puzzle){alert('문제 생성 실패');return;}
  cars=JSON.parse(JSON.stringify(puzzle));
  currentLevel=classifyDifficulty(solvePuzzle(cars));
  startDiv.classList.add('hidden');
  dialog.classList.add('hidden');
  canvas.classList.remove('hidden');
  draw();
}

startDiv.querySelectorAll('button').forEach(btn=>{
  btn.addEventListener('click',()=>startGame(parseInt(btn.dataset.level,10)));
});

restartBtn.onclick=()=>{
  dialog.classList.add('hidden');
  canvas.classList.add('hidden');
  startDiv.classList.remove('hidden');
  cars=[];
  selected=null;
};
