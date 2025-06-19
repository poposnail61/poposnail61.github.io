export function randColor(){
  return 'hsl(' + Math.random()*360 + ',60%,70%)';
}

function copyCars(cars){
  return cars.map(c=>({x:c.x,y:c.y,length:c.length,dir:c.dir,color:c.color,red:c.red}));
}

function boardKey(cars){
  return cars.map(c=>c.x+','+c.y).join('|');
}

function isFree(x,y,cars,ignore,boardSize){
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

export function solvePuzzle(startCars,boardSize=6,maxDepth=40){
  const exitRow=2;
  const start=copyCars(startCars);
  const queue=[{cars:start,depth:0}];
  const visited=new Set();
  while(queue.length){
    const {cars,depth}=queue.shift();
    const key=boardKey(cars);
    if(visited.has(key))continue;
    visited.add(key);
    const red=cars.find(c=>c.red);
    if(red.x+red.length===boardSize&&red.y===exitRow)return depth;
    if(depth>=maxDepth)continue;
    for(let i=0;i<cars.length;i++){
      const car=cars[i];
      if(car.dir==='H'){
        for(let nx=car.x-1;isFree(nx,car.y,cars,car,boardSize);nx--){
          const next=copyCars(cars);next[i].x=nx;queue.push({cars:next,depth:depth+1});
        }
        for(let nx=car.x+1;isFree(nx+car.length-1,car.y,cars,car,boardSize);nx++){
          const next=copyCars(cars);next[i].x=nx;queue.push({cars:next,depth:depth+1});
        }
      }else{
        for(let ny=car.y-1;isFree(car.x,ny,cars,car,boardSize);ny--){
          const next=copyCars(cars);next[i].y=ny;queue.push({cars:next,depth:depth+1});
        }
        for(let ny=car.y+1;isFree(car.x,ny+car.length-1,cars,car,boardSize);ny++){
          const next=copyCars(cars);next[i].y=ny;queue.push({cars:next,depth:depth+1});
        }
      }
    }
  }
  return -1;
}

export function classifyDifficulty(moves){
  if(moves<=10)return 1;
  if(moves<=20)return 2;
  if(moves<=30)return 3;
  if(moves<=40)return 4;
  return 5;
}

export function generatePuzzleByDifficulty(level,boardSize=6){
  for(let i=0;i<1000;i++){
    const puzzle=generateRandomPuzzle(boardSize);
    const moves=solvePuzzle(puzzle,boardSize,60);
    if(moves>0&&classifyDifficulty(moves)===level)return puzzle;
  }
  return null;
}

export function generateRandomPuzzle(boardSize=6){
  const cars=[{x:0,y:2,length:2,dir:'H',color:'red',red:true}];
  let attempts=0;
  while(cars.length<8&&attempts<200){
    attempts++;
    const dir=Math.random()<0.5?'H':'V';
    const length=Math.random()<0.7?2:3;
    const x=Math.floor(Math.random()*(dir==='H'?boardSize-length+1:boardSize));
    const y=Math.floor(Math.random()*(dir==='V'?boardSize-length+1:boardSize));
    let overlap=false;
    for(const c of cars){
      for(let i=0;i<length;i++){
        const cx=dir==='H'?x+i:x;
        const cy=dir==='V'?y+i:y;
        for(let j=0;j<c.length;j++){
          const ox=c.dir==='H'?c.x+j:c.x;
          const oy=c.dir==='V'?c.y+j:c.y;
          if(cx===ox&&cy===oy){overlap=true;break;}
        }
        if(overlap)break;
      }
      if(overlap)break;
    }
    if(!overlap)cars.push({x,y,length,dir,color:randColor()});
  }
  return cars;
}

export const defaultPuzzles=Array.from({length:50},()=>generateRandomPuzzle());
