export function randColor(){
  return 'hsl(' + Math.random()*360 + ',60%,70%)';
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
