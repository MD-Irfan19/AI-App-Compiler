'use client'

import { useState, useEffect } from 'react'

interface AnimatedPlaceholderProps {
  examples: string[]
  cycleInterval?: number
  typingSpeed?: number
}

export function useAnimatedPlaceholder({ 
  examples, 
  cycleInterval = 3500, 
  typingSpeed = 50 
}: AnimatedPlaceholderProps) {
  const [displayText, setDisplayText] = useState('')
  const [currentExampleIndex, setCurrentExampleIndex] = useState(0)
  const [isTyping, setIsTyping] = useState(true)

  useEffect(() => {
    const currentExample = examples[currentExampleIndex]
    
    if (isTyping) {
      // Typing effect
      if (displayText.length < currentExample.length) {
        const timeout = setTimeout(() => {
          setDisplayText(currentExample.slice(0, displayText.length + 1))
        }, typingSpeed)
        return () => clearTimeout(timeout)
      } else {
        // Finished typing, wait before switching
        const timeout = setTimeout(() => {
          setIsTyping(false)
        }, cycleInterval - currentExample.length * typingSpeed)
        return () => clearTimeout(timeout)
      }
    } else {
      // Deleting effect
      if (displayText.length > 0) {
        const timeout = setTimeout(() => {
          setDisplayText(displayText.slice(0, -1))
        }, 20) // Fast delete
        return () => clearTimeout(timeout)
      } else {
        // Move to next example
        setCurrentExampleIndex((prev) => (prev + 1) % examples.length)
        setIsTyping(true)
      }
    }
  }, [displayText, isTyping, currentExampleIndex, examples, cycleInterval, typingSpeed])

  return displayText
}
