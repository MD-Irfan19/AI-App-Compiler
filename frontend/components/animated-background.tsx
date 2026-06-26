'use client'

import { motion } from 'framer-motion'

export function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Deep dark base */}
      <div className="absolute inset-0 bg-[oklch(0.02_0.005_260)]" />
      
      {/* Base gradient layer */}
      <div className="absolute inset-0 animated-bg opacity-80" />
      
      {/* Floating orbs - more subtle for darker theme */}
      <motion.div
        className="absolute w-[700px] h-[700px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.45 0.18 240 / 25%) 0%, transparent 65%)',
          top: '-15%',
          left: '-15%',
        }}
        animate={{
          x: [0, 120, 60, 0],
          y: [0, 60, 120, 0],
          scale: [1, 1.15, 0.95, 1],
        }}
        transition={{
          duration: 30,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      
      <motion.div
        className="absolute w-[550px] h-[550px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.55 0.12 40 / 22%) 0%, transparent 65%)',
          top: '15%',
          right: '-8%',
        }}
        animate={{
          x: [0, -100, -50, 0],
          y: [0, 100, -40, 0],
          scale: [1, 0.9, 1.1, 1],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      
      <motion.div
        className="absolute w-[450px] h-[450px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.5 0.16 240 / 20%) 0%, transparent 65%)',
          bottom: '5%',
          left: '15%',
        }}
        animate={{
          x: [0, 80, -50, 0],
          y: [0, -80, 50, 0],
          scale: [1, 1.2, 0.85, 1],
        }}
        transition={{
          duration: 28,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Additional gradient orbs for more visual depth */}
      <motion.div
        className="absolute w-[350px] h-[350px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.65 0.1 38 / 18%) 0%, transparent 65%)',
          top: '50%',
          right: '10%',
        }}
        animate={{
          x: [0, -60, 40, 0],
          y: [0, 60, -80, 0],
          scale: [1, 0.95, 1.1, 1],
        }}
        transition={{
          duration: 32,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      <motion.div
        className="absolute w-[400px] h-[400px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.6 0.15 240 / 16%) 0%, transparent 65%)',
          bottom: '20%',
          right: '20%',
        }}
        animate={{
          x: [0, 100, -30, 0],
          y: [0, -70, 40, 0],
          scale: [1, 1.1, 0.9, 1],
        }}
        transition={{
          duration: 26,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      <motion.div
        className="absolute w-[300px] h-[300px] rounded-full"
        style={{
          background: 'radial-gradient(circle, oklch(0.55 0.14 40 / 17%) 0%, transparent 65%)',
          top: '35%',
          left: '5%',
        }}
        animate={{
          x: [0, 80, -40, 0],
          y: [0, -60, 70, 0],
          scale: [1, 1.15, 0.85, 1],
        }}
        transition={{
          duration: 24,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Light streaks - enhanced visibility on darker background */}
      {[...Array(10)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute h-[2px]"
          style={{
            width: `${180 + i * 60}px`,
            background: i % 2 === 0 
              ? 'linear-gradient(90deg, transparent, oklch(0.65 0.18 240 / 85%), oklch(0.7 0.12 40 / 60%), transparent)'
              : 'linear-gradient(90deg, transparent, oklch(0.7 0.12 40 / 75%), oklch(0.65 0.18 240 / 50%), transparent)',
            top: `${12 + i * 13}%`,
            left: '-25%',
            filter: 'blur(0.5px)',
            boxShadow: i % 2 === 0 
              ? '0 0 24px oklch(0.65 0.18 240 / 60%), 0 0 48px oklch(0.65 0.18 240 / 30%)' 
              : '0 0 24px oklch(0.7 0.12 40 / 60%), 0 0 48px oklch(0.7 0.12 40 / 30%)',
          }}
          animate={{
            x: ['-100%', '160vw'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 10 + i * 2.5,
            repeat: Infinity,
            delay: i * 1.8,
            ease: 'linear',
          }}
        />
      ))}

      {/* Reverse direction streaks */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={`reverse-${i}`}
          className="absolute h-[2px]"
          style={{
            width: `${140 + i * 45}px`,
            background: i % 2 === 0 
              ? 'linear-gradient(90deg, transparent, oklch(0.6 0.16 240 / 75%), transparent)'
              : 'linear-gradient(90deg, transparent, oklch(0.65 0.1 38 / 70%), transparent)',
            top: `${22 + i * 18}%`,
            right: '-25%',
            filter: 'blur(0.5px)',
            boxShadow: i % 2 === 0 
              ? '0 0 20px oklch(0.6 0.16 240 / 55%), 0 0 40px oklch(0.6 0.16 240 / 25%)' 
              : '0 0 20px oklch(0.65 0.1 38 / 55%), 0 0 40px oklch(0.65 0.1 38 / 25%)',
          }}
          animate={{
            x: ['100%', '-160vw'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 12 + i * 2.5,
            repeat: Infinity,
            delay: i * 2.5 + 4,
            ease: 'linear',
          }}
        />
      ))}

      {/* Subtle noise overlay - reduced for cleaner dark look */}
      <div 
        className="absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Enhanced vignette for deeper dark edges */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 0%, oklch(0.02 0.005 260 / 70%) 100%)',
        }}
      />
      
      {/* Top-down gradient overlay for depth */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(180deg, oklch(0.01 0.005 260 / 40%) 0%, transparent 30%, transparent 70%, oklch(0.01 0.005 260 / 50%) 100%)',
        }}
      />
    </div>
  )
}
