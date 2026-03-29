import { useCallback } from "react";
import Particles from "react-tsparticles";
import { loadFull } from "tsparticles";

export default function ParticleHero() {
  const particlesInit = useCallback(async (engine: any) => {
    await loadFull(engine);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden" style={{ transform: "translateZ(0)" }}>
      <Particles
        id="hero-particles"
        init={particlesInit}
        style={{
          width: "100%",
          height: "100%",
          position: "absolute",
        }}
        options={{
          background: {
            color: { value: "transparent" },
          },
          fpsLimit: 60,
          fullScreen: false,
          pauseOnBlur: true,
          pauseOnOutsideViewport: true,
          interactivity: {
            events: {
              resize: true,
              onHover: {
                enable: true,
                mode: "grab",
                parallax: {
                  enable: true,
                  force: 30,
                  smooth: 30,
                },
              },
            },
            modes: {
              grab: {
                distance: 150,
                links: { opacity: 0.2 },
              },
            },
          },
          particles: {
            color: {
              value: ["#a6daff", "#ffffff", "#7cb8e0"],
            },
            collisions: { enable: false },
            move: {
              direction: "none" as const,
              enable: true,
              outModes: { default: "out" as const },
              random: true,
              speed: 0.6,
              straight: false,
            },
            links: {
              enable: true,
              color: "#a6daff",
              opacity: 0.07,
              distance: 180,
              width: 1,
            },
            number: {
              value: 80,
              density: {
                enable: true,
                area: 1200,
              },
            },
            opacity: {
              value: { min: 0.1, max: 0.5 },
            },
            shape: {
              type: "circle",
            },
            size: {
              value: { min: 0.5, max: 2.5 },
            },
          },
          detectRetina: true,
        }}
      />
    </div>
  );
}
