import { motion } from "framer-motion";
import { useMemo } from "react";

function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  duration: number;
  delay: number;
  driftX: number;
  driftY: number;
}

export function ParticleBackground() {
  const particles = useMemo(() => {
    const result: Particle[] = [];
    for (let i = 0; i < 45; i++) {
      result.push({
        id: i,
        x: seededRandom(i * 7 + 1) * 100,
        y: seededRandom(i * 13 + 3) * 100,
        size: 1.5 + seededRandom(i * 19 + 5) * 2.5,
        opacity: 0.08 + seededRandom(i * 23 + 7) * 0.25,
        duration: 18 + seededRandom(i * 29 + 11) * 25,
        delay: seededRandom(i * 31 + 13) * 10,
        driftX: (seededRandom(i * 37 + 17) - 0.5) * 60,
        driftY: (seededRandom(i * 41 + 19) - 0.5) * 80,
      });
    }
    return result;
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-[#8B9BB4]"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            opacity: p.opacity,
          }}
          animate={{
            x: [0, p.driftX, -p.driftX * 0.5, 0],
            y: [0, p.driftY, -p.driftY * 0.3, 0],
            opacity: [p.opacity, p.opacity * 1.5, p.opacity * 0.6, p.opacity],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        />
      ))}
    </div>
  );
}
