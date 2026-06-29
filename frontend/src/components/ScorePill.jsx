export default function ScorePill({ score }) {
  return (
    <div className="score-pill">
      <strong>{score?.total ?? 0}</strong>
    </div>
  );
}
