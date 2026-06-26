'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain,
  Layers,
  Database,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  Activity,
  Shield,
  Code2,
  Layout,
  GitBranch,
  RefreshCw,
} from 'lucide-react'
import { AnimatedBackground } from '@/components/animated-background'
import { useAnimatedPlaceholder } from '@/components/animated-placeholder'

// ─────────────────────────────────────────────
// TYPES — fixed to match exact backend response
// ─────────────────────────────────────────────

interface Feature {
  name: string
  description: string
  requires_auth?: boolean
  roles_allowed?: string[]
}

interface IntentLayer {
  app_name: string
  app_type: string
  description: string
  user_roles: string[]
  core_features: Feature[]
  assumptions: string[]
  clarifications_needed?: string[]
  has_payments?: boolean
  has_analytics?: boolean
}

interface TableField {
  name: string
  type: string
  primary_key?: boolean
  foreign_key?: string | null
  required?: boolean
  unique?: boolean
}

interface DatabaseTable {
  name: string
  fields: TableField[]
  relations?: { type: string; target_table: string }[]
}

interface ApiEndpoint {
  method: string
  path: string
  description: string
  roles_allowed: string[]
  auth_required?: boolean
  request_body?: { name: string; type: string; required: boolean }[]
  response_fields?: { name: string; type: string; required: boolean }[]
}

interface UIComponent {
  id: string
  type: string
  label: string
  data_source?: string
  fields?: (string | { name: string })[]
  actions?: (string | { label: string })[]
  visible_to_roles?: string[]
}

interface UiPage {
  name: string
  path: string
  title?: string
  auth_required: boolean
  roles_allowed: string[]  // ← backend uses roles_allowed not roles
  components: UIComponent[]
}

interface Permission {
  resource: string
  actions: string[]
}

interface AuthRole {
  role: string
  permissions: Permission[]
  can_access_premium?: boolean
}

interface BusinessRule {
  name: string
  description?: string
  trigger: string
  actions: string[]
  applies_to_roles?: string[]
}

interface StageResult {
  stage: string
  status: string
  duration_ms: number
  output_summary: Record<string, unknown>
}

interface ValidationResult {
  is_valid: boolean
  errors: unknown[]
  warnings: unknown[]
}

interface AppConfig {
  intent: IntentLayer
  database: { tables: DatabaseTable[] }
  api: { base_path: string; endpoints: ApiEndpoint[] }
  ui: { pages: UiPage[]; theme: string; nav_items: (string | { label: string; path: string })[] }
  auth: { roles: AuthRole[]; jwt_enabled: boolean; session_timeout_minutes: number }
  business_logic: { rules: BusinessRule[]; payment_gateway: string | null; premium_features: string[] }
  system_design: unknown
  generation_metadata: Record<string, unknown>
}

// ── Main response shape from backend ──
interface CompileResponse {
  success: boolean
  prompt: string
  app_config: AppConfig           // ← all data lives here
  stages: StageResult[]           // ← not pipeline_stages
  validation: ValidationResult    // ← not consistency_check
  total_duration_ms: number
  timestamp: string
  generated_app_path?: string | null
}

interface Metrics {
  total_runs: number
  success_rate: string            // ← backend returns string like "100.0%"
  average_duration_ms: number     // ← not avg_duration_ms
  recent_runs: {
    timestamp: string
    success: boolean
    total_duration_ms: number     // ← not duration_ms
  }[]
}

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

const PIPELINE_STEPS = [
  { id: 1, name: 'Extracting Intent', icon: Brain },
  { id: 2, name: 'Designing Architecture', icon: Layers },
  { id: 3, name: 'Generating Schemas', icon: Database },
  { id: 4, name: 'Refining & Validating', icon: CheckCircle2 },
]

const EXAMPLE_PROMPTS = [
  'CRM with payments and analytics',
  'E-commerce with cart and orders',
  'Project management like Trello',
]

const ANIMATED_PLACEHOLDER_EXAMPLES = [
  'Build a CRM with analytics and payments...',
  'Create an AI-powered resume screening platform...',
  'Build a food delivery app for college campuses...',
  'Create a SaaS to track startup KPIs...',
  'Build a hospital management system...',
]

const STAGE_TO_STEP: Record<string, number> = {
  'intent_extraction': 0,
  'system_design': 1,
  'schema_generation': 2,
  'refinement': 3,
}

const TAB_ITEMS = [
  { id: 'intent', label: 'Intent', icon: Brain },
  { id: 'database', label: 'Database', icon: Database },
  { id: 'api', label: 'API', icon: Code2 },
  { id: 'ui', label: 'UI Pages', icon: Layout },
  { id: 'auth', label: 'Auth', icon: Shield },
  { id: 'logic', label: 'Business Logic', icon: GitBranch },
  { id: 'json', label: 'Raw JSON', icon: Code2 },
]

// ─────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────

export default function AIAppCompiler() {
  const pipelineProgressRef = useRef<HTMLElement>(null)

  const [prompt, setPrompt] = useState('')
  const [generateFiles, setGenerateFiles] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [elapsedTime, setElapsedTime] = useState(0)
  const [result, setResult] = useState<CompileResponse | null>(null)
  const [error, setError] = useState<{ message: string; stage?: string } | null>(null)
  const [activeTab, setActiveTab] = useState('intent')
  const [copied, setCopied] = useState(false)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [metricsExpanded, setMetricsExpanded] = useState(false)
  const [liveStages, setLiveStages] = useState<StageResult[]>([])
  const [activeSubsteps, setActiveSubsteps] = useState<string[]>([])
  const abortControllerRef = useRef<AbortController | null>(null)

  const animatedPlaceholder = useAnimatedPlaceholder({
    examples: ANIMATED_PLACEHOLDER_EXAMPLES,
    cycleInterval: 3500,
    typingSpeed: 50,
  })

  // Fetch metrics on mount
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('http://localhost:8000/metrics')
        if (res.ok) {
          const data = await res.json()
          setMetrics(data)
        }
      } catch {
        // Silently fail
      }
    }
    fetchMetrics()
  }, [])

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isCompiling) {
      interval = setInterval(() => setElapsedTime((p) => p + 100), 100)
    }
    return () => clearInterval(interval)
  }, [isCompiling])

  const handleCompile = useCallback(async () => {
    if (!prompt.trim()) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    setIsCompiling(true)
    setCurrentStep(0)
    setCompletedSteps([])
    setLiveStages([])
    setActiveSubsteps([])
    setElapsedTime(0)
    setResult(null)
    setError(null)

    setTimeout(() => {
      pipelineProgressRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)

    try {
      const res = await fetch('http://localhost:8000/compile/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          generate_app_files: generateFiles,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        const detail = errorData.detail
        throw new Error(
          typeof detail === 'object'
            ? detail.error || JSON.stringify(detail)
            : detail || 'Compilation failed'
        )
      }

      if (!res.body) throw new Error("No response body")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const dataStr = part.slice(6)
          
          let event
          try {
            event = JSON.parse(dataStr)
          } catch (e) {
            console.error("Failed to parse event:", dataStr, e)
            continue
          }
          
          if (event.type === 'stage_start') {
            setCurrentStep(STAGE_TO_STEP[event.stage] ?? 0)
          } else if (event.type === 'stage_done') {
            const stepIdx = STAGE_TO_STEP[event.stage]
            if (stepIdx !== undefined) {
              setCompletedSteps((prev) => {
                 if (!prev.includes(stepIdx + 1)) return [...prev, stepIdx + 1]
                 return prev
              })
            }
            setLiveStages((prev) => [
              ...prev,
              {
                stage: event.stage,
                status: 'success',
                duration_ms: event.duration_ms,
                output_summary: event.output_summary,
              }
            ])
            if (event.stage === 'schema_generation') {
              setActiveSubsteps([])
            }
          } else if (event.type === 'substep_done') {
            setActiveSubsteps((prev) => [...prev, event.substep.replace(/_/g, ' ')])
          } else if (event.type === 'complete') {
            setResult(event.data)
            setCompletedSteps([1, 2, 3, 4])
            setCurrentStep(4)
            setElapsedTime(event.data.total_duration_ms)
            setIsCompiling(false)
          } else if (event.type === 'error') {
            setError({ message: event.message, stage: event.stage?.replace(/_/g, ' ') || PIPELINE_STEPS[currentStep]?.name })
            setIsCompiling(false)
            reader.cancel()
            break
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return
      setError({
        message: err.message || 'An unexpected error occurred',
        stage: PIPELINE_STEPS[currentStep]?.name,
      })
      setIsCompiling(false)
    }
  }, [prompt, generateFiles, currentStep])

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handleCopyJson = useCallback(() => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [result])

  const handleExampleClick = useCallback((example: string) => {
    setPrompt(example)
  }, [])

  // ── Shorthand for cleaner access
  const config = result?.app_config

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">

        {/* Header — unchanged */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12 pt-16"
        >
          <div className="mb-6 flex items-center justify-center gap-3">
            <Sparkles className="w-10 h-10 text-primary" />
            <h1 className="text-5xl sm:text-6xl font-bold bg-gradient-to-r from-primary via-blue-400 to-primary bg-clip-text text-transparent text-glow-blue">
              AI App Compiler
            </h1>
          </div>
          <p className="text-lg text-muted-foreground mb-6">
            Natural Language → Structured App Configuration
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <motion.span whileHover={{ scale: 1.05 }} className="frost-glass-subtle px-4 py-2 rounded-full text-sm font-medium text-foreground/90 flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />4-Stage Pipeline
            </motion.span>
            <motion.span whileHover={{ scale: 1.05 }} className="frost-glass-subtle px-4 py-2 rounded-full text-sm font-medium text-foreground/90 flex items-center gap-2">
              <Zap className="w-4 h-4 text-accent" />Powered by Nvidia NIM
            </motion.span>
            <motion.span whileHover={{ scale: 1.05 }} className="frost-glass-subtle px-4 py-2 rounded-full text-sm font-medium text-foreground/90 flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />Enterprise-Ready Schemas
            </motion.span>
            <motion.span whileHover={{ scale: 1.05 }} className="frost-glass-subtle px-4 py-2 rounded-full text-sm font-medium text-foreground/90 flex items-center gap-2">
              <Brain className="w-4 h-4 text-accent" />AI-Powered Architecture
            </motion.span>
          </div>
        </motion.header>

        {/* Input Section — unchanged */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-8"
        >
          <div className="frost-glass-strong rounded-2xl p-6 sm:p-8 flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <label htmlFor="prompt" className="block text-lg font-medium text-foreground/80 mb-3">
                What Should We Build Today?
              </label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={animatedPlaceholder}
                className="w-full h-36 bg-[oklch(0.04_0.005_260_/_60%)] border border-border/40 rounded-xl px-4 py-3 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all duration-300 resize-none font-mono text-sm"
                disabled={isCompiling}
              />
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-4">
                <label className="flex items-center gap-3 cursor-pointer group px-4 py-3 frost-glass-subtle rounded-lg hover:bg-primary/5 transition-all duration-300">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={generateFiles}
                      onChange={(e) => setGenerateFiles(e.target.checked)}
                      className="sr-only peer"
                      disabled={isCompiling}
                    />
                    <div className="w-12 h-7 bg-gradient-to-r from-muted to-muted/60 rounded-full peer peer-checked:from-primary peer-checked:to-primary/80 transition-all duration-300 shadow-md peer-checked:shadow-lg peer-checked:glow-blue" />
                    <div className="absolute left-0.5 top-0.5 w-6 h-6 bg-foreground rounded-full transition-all duration-300 peer-checked:translate-x-5 shadow-sm peer-checked:shadow-primary/30" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">Generate App Files</span>
                    <span className="text-xs text-muted-foreground">{generateFiles ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </label>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCompile}
                  disabled={isCompiling || !prompt.trim()}
                  className="px-8 py-3 bg-gradient-to-r from-primary to-blue-500 text-primary-foreground font-semibold rounded-xl shadow-lg glow-blue disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center gap-2"
                >
                  {isCompiling ? (
                    <><RefreshCw className="w-5 h-5 animate-spin" />Compiling...</>
                  ) : (
                    <><Sparkles className="w-5 h-5" />Compile App</>
                  )}
                </motion.button>
              </div>
              <div className="mt-6 pt-6 border-t border-border/30">
                <p className="text-xs text-muted-foreground mb-3">Try an example:</p>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_PROMPTS.map((example) => (
                    <motion.button
                      key={example}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => handleExampleClick(example)}
                      disabled={isCompiling}
                      className="px-4 py-2 frost-glass-subtle rounded-full text-sm text-foreground/70 hover:text-foreground hover:border-primary/20 transition-all duration-300 disabled:opacity-50"
                    >
                      {example}
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.section>

        {/* Pipeline Progress — unchanged */}
        <AnimatePresence>
          {isCompiling && (
            <motion.section
              ref={pipelineProgressRef}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8 overflow-hidden"
            >
              <div className="frost-glass rounded-2xl p-6 flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                  <Activity className="w-6 h-6 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-foreground">Pipeline Progress</h3>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Clock className="w-4 h-4" />
                      {(elapsedTime / 1000).toFixed(1)}s
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {PIPELINE_STEPS.map((step, index) => {
                      const Icon = step.icon
                      const isActive = currentStep === index
                      const isCompleted = completedSteps.includes(step.id)
                      return (
                        <motion.div
                          key={step.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className={`frost-glass-subtle rounded-xl p-4 transition-all duration-500 ${isCompleted ? 'border-green-500/30 bg-green-500/5'
                                : isActive ? 'border-primary/50 bg-primary/5 glow-blue' : ''
                            }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${isCompleted ? 'bg-green-500/20 text-green-400'
                                  : isActive ? 'bg-primary/20 text-primary animate-pulse'
                                    : 'bg-muted/30 text-muted-foreground'
                              }`}>
                              {isCompleted ? <Check className="w-5 h-5" />
                                  : <Icon className="w-5 h-5" />}
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Step {step.id}</p>
                              <p className={`text-sm font-medium transition-colors ${isCompleted ? 'text-green-400'
                                    : isActive ? 'text-primary'
                                      : 'text-foreground/60'
                                }`}>
                                {step.name}
                              </p>
                              {isActive && step.id === 3 && activeSubsteps.length > 0 && (
                                <motion.p
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  transition={{ duration: 0.5 }}
                                  className="text-xs text-muted-foreground mt-1 capitalize"
                                >
                                  {activeSubsteps[activeSubsteps.length - 1]} done...
                                </motion.p>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Error State — unchanged */}
        <AnimatePresence>
          {error && (
            <motion.section
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mb-8"
            >
              <div className="frost-glass rounded-2xl p-6 border-destructive/30 bg-destructive/5">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full bg-destructive/20 flex items-center justify-center flex-shrink-0">
                    <AlertCircle className="w-6 h-6 text-destructive" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-destructive mb-1">Compilation Failed</h3>
                    <p className="text-foreground/80 mb-2">{error.message}</p>
                    {error.stage && (
                      <p className="text-sm text-muted-foreground">
                        Failed at: <span className="text-foreground/80">{error.stage}</span>
                      </p>
                    )}
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleCompile}
                      className="mt-4 px-6 py-2 bg-destructive/20 text-destructive font-medium rounded-lg hover:bg-destructive/30 transition-colors"
                    >
                      Try Again
                    </motion.button>
                  </div>
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Results Section — fixed data mapping only */}
        <AnimatePresence>
          {result && config && (
            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              {/* Summary Bar */}
              <div className="frost-glass-strong rounded-2xl p-4 sm:p-6 mb-6 flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-6 h-6 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">App Name</p>
                      <p className="font-semibold text-foreground truncate">
                        {config.intent?.app_name ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">App Type</p>
                      <p className="font-semibold text-foreground truncate">
                        {config.intent?.app_type ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Total Duration</p>
                      <p className="font-semibold text-foreground">
                        {result.total_duration_ms
                          ? (result.total_duration_ms / 1000).toFixed(2) + 's'
                          : '0s'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Consistency</p>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${result.validation?.is_valid
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-destructive/20 text-destructive'
                        }`}>
                        {result.validation?.is_valid
                          ? <><Check className="w-3 h-3" /> Valid</>
                          : <><AlertCircle className="w-3 h-3" /> Invalid</>
                        }
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabs and Content */}
              <div className="flex flex-col lg:flex-row gap-6">
                <div className="flex-1">
                  {/* Tab Navigation — unchanged */}
                  <div className="frost-glass rounded-xl p-2 mb-4 overflow-x-auto flex items-center gap-3">
                    <Code2 className="w-5 h-5 text-primary flex-shrink-0" />
                    <div className="flex gap-1 min-w-max">
                      {TAB_ITEMS.map((tab) => {
                        const Icon = tab.icon
                        return (
                          <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${activeTab === tab.id
                              ? 'bg-primary/20 text-primary'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                              }`}
                          >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Tab Content — fixed data sources */}
                  <div className="frost-glass rounded-2xl p-6 min-h-[400px]">
                    <AnimatePresence mode="wait">
                      {activeTab === 'intent' && (
                        <IntentTab key="intent" intent={config.intent} />
                      )}
                      {activeTab === 'database' && (
                        <DatabaseTab key="database" tables={config.database?.tables ?? []} />
                      )}
                      {activeTab === 'api' && (
                        <ApiTab key="api" endpoints={config.api?.endpoints ?? []} />
                      )}
                      {activeTab === 'ui' && (
                        <UiTab key="ui" pages={config.ui?.pages ?? []} />
                      )}
                      {activeTab === 'auth' && (
                        <AuthTab key="auth" roles={config.auth?.roles ?? []} />
                      )}
                      {activeTab === 'logic' && (
                        <LogicTab key="logic" rules={config.business_logic?.rules ?? []} />
                      )}
                      {activeTab === 'json' && (
                        <JsonTab key="json" data={result} copied={copied} onCopy={handleCopyJson} />
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Pipeline Stages Sidebar — fixed field names */}
                <div className="lg:w-64">
                  <div className="frost-glass rounded-2xl p-4">
                    <h4 className="text-sm font-semibold text-foreground mb-4">Pipeline Stages</h4>
                    <div className="space-y-3">
                      {(result ? result.stages : liveStages).map((stage, index) => (
                        <div key={index} className="flex items-center justify-between p-3 frost-glass-subtle rounded-lg">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate capitalize">
                              {stage.stage.replace(/_/g, ' ')}
                            </p>
                            <p className="text-xs text-muted-foreground">{stage.duration_ms}ms</p>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${stage.status === 'success'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-destructive/20 text-destructive'
                            }`}>
                            {stage.status === 'success' ? 'OK' : 'Fail'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Metrics Panel — fixed field names */}
        {metrics && (
          <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-8"
          >
            <div className="frost-glass rounded-2xl overflow-hidden">
              <button
                onClick={() => setMetricsExpanded(!metricsExpanded)}
                className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-muted/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-primary" />
                  <span className="font-medium text-foreground">System Metrics</span>
                </div>
                {metricsExpanded
                  ? <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  : <ChevronDown className="w-5 h-5 text-muted-foreground" />
                }
              </button>
              <AnimatePresence>
                {metricsExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-border/30"
                  >
                    <div className="p-6">
                      <div className="grid grid-cols-3 gap-4 mb-6">
                        <div className="frost-glass-subtle rounded-xl p-4 text-center">
                          <p className="text-2xl font-bold text-primary">{metrics.total_runs}</p>
                          <p className="text-xs text-muted-foreground">Total Runs</p>
                        </div>
                        <div className="frost-glass-subtle rounded-xl p-4 text-center">
                          <p className="text-2xl font-bold text-green-400">
                            {metrics.success_rate}
                          </p>
                          <p className="text-xs text-muted-foreground">Success Rate</p>
                        </div>
                        <div className="frost-glass-subtle rounded-xl p-4 text-center">
                          <p className="text-2xl font-bold text-accent">
                            {((metrics.average_duration_ms ?? 0) / 1000).toFixed(2)}s
                          </p>
                          <p className="text-xs text-muted-foreground">Avg Duration</p>
                        </div>
                      </div>
                      {(metrics.recent_runs ?? []).length > 0 && (
                        <div>
                          <h5 className="text-sm font-medium text-foreground mb-3">Recent Runs</h5>
                          <div className="space-y-2">
                            {metrics.recent_runs.slice(0, 5).map((run, index) => (
                              <div key={index} className="flex items-center justify-between p-2 frost-glass-subtle rounded-lg text-sm">
                                <span className="text-muted-foreground text-xs">
                                  {new Date(run.timestamp).toLocaleTimeString()}
                                </span>
                                <div className="flex items-center gap-3">
                                  <span className="text-foreground/80">
                                    {((run.total_duration_ms ?? 0) / 1000).toFixed(2)}s
                                  </span>
                                  <span className={`w-2 h-2 rounded-full ${run.success ? 'bg-green-400' : 'bg-destructive'
                                    }`} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.section>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// TAB COMPONENTS — all UI unchanged, only data access fixed
// ─────────────────────────────────────────────

function IntentTab({ intent }: { intent: IntentLayer | undefined }) {
  if (!intent) return null
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="space-y-6"
    >
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Description</h4>
        <p className="text-foreground">{intent.description}</p>
      </div>
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">User Roles</h4>
        <div className="flex flex-wrap gap-2">
          {(intent.user_roles ?? []).map((role) => (
            <span key={role} className="px-3 py-1 bg-primary/20 text-primary rounded-full text-sm font-medium">
              {role}
            </span>
          ))}
        </div>
      </div>
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-3">Core Features</h4>
        <div className="grid gap-3">
          {(intent.core_features ?? []).map((feature, index) => (
            <div key={index} className="frost-glass-subtle rounded-xl p-4">
              <h5 className="font-medium text-foreground mb-1">{feature.name}</h5>
              <p className="text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
      {(intent.assumptions ?? []).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">Assumptions</h4>
          <ul className="space-y-2">
            {intent.assumptions.map((assumption, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-amber-400/90 bg-amber-500/10 rounded-lg px-3 py-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                {assumption}
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  )
}

function DatabaseTab({ tables }: { tables: DatabaseTable[] }) {
  if (!tables?.length) return (
    <p className="text-muted-foreground text-sm">No tables generated.</p>
  )
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="grid gap-4"
    >
      {tables.map((table) => (
        <div key={table.name} className="frost-glass-subtle rounded-xl p-4">
          <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
            <Database className="w-4 h-4 text-primary" />
            {table.name}
          </h4>
          <div className="space-y-2">
            {(table.fields ?? []).map((field) => (
              <div key={field.name} className="flex items-center justify-between text-sm p-2 bg-[oklch(0.04_0.005_260_/_50%)] rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-foreground">{field.name}</span>
                  <span className="text-muted-foreground">{field.type}</span>
                </div>
                <div className="flex gap-2">
                  {field.primary_key && (
                    <span className="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs font-medium">PK</span>
                  )}
                  {field.foreign_key && (
                    <span className="px-2 py-0.5 bg-accent/20 text-accent rounded text-xs font-medium">
                      FK → {field.foreign_key}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  )
}

function ApiTab({ endpoints }: { endpoints: ApiEndpoint[] }) {
  const methodColors: Record<string, string> = {
    GET: 'bg-green-500/20 text-green-400',
    POST: 'bg-primary/20 text-primary',
    PUT: 'bg-amber-500/20 text-amber-400',
    DELETE: 'bg-destructive/20 text-destructive',
    PATCH: 'bg-purple-500/20 text-purple-400',
  }
  if (!endpoints?.length) return (
    <p className="text-muted-foreground text-sm">No endpoints generated.</p>
  )
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="space-y-3"
    >
      {endpoints.map((endpoint, index) => (
        <div key={index} className="frost-glass-subtle rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-3">
          <span className={`px-3 py-1 rounded-lg text-xs font-bold w-fit ${methodColors[endpoint.method] ?? 'bg-muted/30 text-muted-foreground'
            }`}>
            {endpoint.method}
          </span>
          <code className="font-mono text-sm text-foreground flex-1">{endpoint.path}</code>
          <p className="text-sm text-muted-foreground flex-1">{endpoint.description}</p>
          <div className="flex flex-wrap gap-1">
            {(endpoint.roles_allowed ?? []).map((role) => (
              <span key={role} className="px-2 py-0.5 bg-muted/30 text-muted-foreground rounded text-xs">
                {role}
              </span>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  )
}

function UiTab({ pages }: { pages: UiPage[] }) {
  if (!pages?.length) return (
    <p className="text-muted-foreground text-sm">No pages generated.</p>
  )
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="grid sm:grid-cols-2 gap-4"
    >
      {pages.map((page) => (
        <div key={page.path} className="frost-glass-subtle rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <code className="font-mono text-sm text-foreground">{page.path}</code>
            {page.auth_required && (
              <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs font-medium">
                Auth Required
              </span>
            )}
          </div>
          {(page.roles_allowed ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {page.roles_allowed.map((role) => (
                <span key={role} className="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs">
                  {role}
                </span>
              ))}
            </div>
          )}
          <div>
            <p className="text-xs text-muted-foreground mb-2">
              Components ({page.components?.length ?? 0})
            </p>
            <ul className="space-y-1">
              {(page.components ?? []).map((component, index) => (
                <li key={index} className="text-sm text-foreground/80 flex items-center gap-2">
                  <Layout className="w-3 h-3 text-muted-foreground" />
                  {component.label ?? component.type ?? component.id}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ))}
    </motion.div>
  )
}

function AuthTab({ roles }: { roles: AuthRole[] }) {
  if (!roles?.length) return (
    <p className="text-muted-foreground text-sm">No roles generated.</p>
  )
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="grid sm:grid-cols-2 gap-4"
    >
      {roles.map((role) => (
        <div key={role.role} className="frost-glass-subtle rounded-xl p-4">
          <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            {role.role}
          </h4>
          <div className="space-y-2">
            {(role.permissions ?? []).map((perm, index) => (
              <div key={index} className="text-sm">
                <p className="font-medium text-foreground/90 mb-1">{perm.resource}</p>
                <div className="flex flex-wrap gap-1">
                  {(perm.actions ?? []).map((action) => (
                    <span key={action} className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded text-xs">
                      {action}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  )
}

function LogicTab({ rules }: { rules: BusinessRule[] }) {
  if (!rules?.length) return (
    <p className="text-muted-foreground text-sm">No business rules generated.</p>
  )
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="space-y-4"
    >
      {rules.map((rule, index) => (
        <div key={index} className="frost-glass-subtle rounded-xl p-4">
          <div className="flex items-start justify-between mb-3">
            <h4 className="font-semibold text-foreground">{rule.name}</h4>
            <span className="px-3 py-1 bg-accent/20 text-accent rounded-full text-xs font-medium ml-2">
              {rule.trigger}
            </span>
          </div>
          {rule.description && (
            <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
          )}
          <ul className="space-y-1">
            {(rule.actions ?? []).map((action, actionIndex) => (
              <li key={actionIndex} className="text-sm text-foreground/80 flex items-center gap-2">
                <Zap className="w-3 h-3 text-primary" />
                {action}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </motion.div>
  )
}

function JsonTab({
  data,
  copied,
  onCopy,
}: {
  data: CompileResponse
  copied: boolean
  onCopy: () => void
}) {
  const [expanded, setExpanded] = useState(true)
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
    >
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {expanded ? 'Collapse' : 'Expand'} JSON
        </button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onCopy}
          className="flex items-center gap-2 px-4 py-2 frost-glass-subtle rounded-lg text-sm font-medium text-foreground hover:bg-muted/30 transition-colors"
        >
          {copied ? (
            <><Check className="w-4 h-4 text-green-400" />Copied!</>
          ) : (
            <><Copy className="w-4 h-4" />Copy JSON</>
          )}
        </motion.button>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <pre className="bg-[oklch(0.03_0.005_260_/_70%)] rounded-xl p-4 overflow-x-auto text-xs font-mono text-foreground/70 max-h-[500px] overflow-y-auto border border-border/30">
              {JSON.stringify(data, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}