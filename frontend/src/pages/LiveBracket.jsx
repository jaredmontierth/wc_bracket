import BracketBoard from "../components/BracketBoard.jsx";

export default function LiveBracket({ tournament }) {
  return (
    <section className="page-panel wide">
      <div className="page-heading">
        <div>
          <h1>Live Bracket</h1>
        </div>
      </div>
      <BracketBoard matches={tournament.matches} picks={{}} onPick={null} actualMode />
    </section>
  );
}
