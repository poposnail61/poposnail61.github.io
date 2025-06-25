import useStore from '../store';

export default function StrokeSlider() {
  const factor = useStore(s => s.factor);
  const setFactor = useStore(s => s.setFactor);
  return (
    <input
      type="range"
      min={0.2}
      max={5}
      step={0.1}
      value={factor}
      onChange={e => setFactor(parseFloat(e.target.value))}
    />
  );
}
