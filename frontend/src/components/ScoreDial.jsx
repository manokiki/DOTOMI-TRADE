/**
 * ScoreDial — l'élément signature de l'interface DOTOMI-TRADE.
 *
 * Plutôt qu'une barre de progression générique, le score 0-100 est rendu
 * comme un cadran d'instrument de précision avec une aiguille — cohérent
 * avec l'identité visuelle du reste de l'interface (cadrans, hairlines,
 * vocabulaire d'instrument de mesure plutôt que de dashboard SaaS).
 *
 * Les zones de seuil (rejeté / faible / surveiller / autorisé) sont
 * dessinées comme des arcs colorés sur le cadran lui-même — l'utilisateur
 * voit immédiatement dans quelle zone tombe le score, pas seulement le
 * chiffre.
 */

const SIZE = 160;
const CENTER = SIZE / 2;
const RADIUS = 64;
const START_ANGLE = -210; // en degrés, 0 = droite, sens horaire
const SWEEP = 240; // amplitude totale du cadran

function angleForScore(score) {
  return START_ANGLE + (score / 100) * SWEEP;
}

function polarToCartesian(angleDeg, radius) {
  const angleRad = (angleDeg * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.cos(angleRad),
    y: CENTER + radius * Math.sin(angleRad),
  };
}

function describeArc(startScore, endScore, radius) {
  const start = polarToCartesian(angleForScore(startScore), radius);
  const end = polarToCartesian(angleForScore(endScore), radius);
  const largeArc = endScore - startScore > 50 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

const ZONES = [
  { from: 0, to: 49, color: "#7A1F1F" }, // rejeté
  { from: 49, to: 70, color: "#8A6A1F" }, // faible
  { from: 70, to: 85, color: "#9C6B14" }, // surveiller
  { from: 85, to: 100, color: "#173404" }, // autorisé
];

export function ScoreDial({ score = 0, status: _status = "REJECTED" }) {
  const needleAngle = angleForScore(Math.max(0, Math.min(100, score)));
  const needleTip = polarToCartesian(needleAngle, RADIUS - 10);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={SIZE} height={SIZE * 0.78} viewBox={`0 0 ${SIZE} ${SIZE * 0.78}`}>
        {ZONES.map((zone) => (
          <path
            key={zone.from}
            d={describeArc(zone.from, zone.to, RADIUS)}
            stroke={zone.color}
            strokeWidth={6}
            fill="none"
            strokeLinecap="butt"
            opacity={0.85}
          />
        ))}

        {/* graduations fines tous les 10 points */}
        {Array.from({ length: 11 }).map((_, i) => {
          const a = angleForScore(i * 10);
          const outer = polarToCartesian(a, RADIUS + 6);
          const inner = polarToCartesian(a, RADIUS + 1);
          return (
            <line
              key={i}
              x1={inner.x}
              y1={inner.y}
              x2={outer.x}
              y2={outer.y}
              stroke="#A6A399"
              strokeWidth={1}
            />
          );
        })}

        {/* aiguille */}
        <line
          x1={CENTER}
          y1={CENTER}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke="#1C1B19"
          strokeWidth={2}
          strokeLinecap="round"
        />
        <circle cx={CENTER} cy={CENTER} r={4} fill="#1C1B19" />
      </svg>

      <div className="-mt-6 text-center">
        <div className="font-display text-4xl tabular tracking-tight text-ink">
          {Math.round(score)}
        </div>
        <div className="text-[11px] uppercase tracking-[0.12em] text-ink-soft">
          score / 100
        </div>
      </div>
    </div>
  );
}
