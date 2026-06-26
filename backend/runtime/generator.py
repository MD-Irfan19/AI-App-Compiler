import os
import json
import logging
from pathlib import Path
from validation.schemas import AppConfig

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info(f"Generated: {path}")


def to_pascal_case(name: str) -> str:
    return "".join(word.capitalize() for word in name.replace("-", "_").replace(" ", "_").split("_"))


def to_kebab_case(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")

# ─────────────────────────────────────────────
# PACKAGE.JSON
# ─────────────────────────────────────────────

def gen_package_json(app_name: str, out: Path):
    content = json.dumps({
        "name": to_kebab_case(app_name),
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start"
        },
        "dependencies": {
            "next": "14.2.0",
            "react": "^18",
            "react-dom": "^18",
            "axios": "^1.6.0",
            "tailwindcss": "^3.4.0",
            "clsx": "^2.1.0"
        },
        "devDependencies": {
            "@types/node": "^20",
            "@types/react": "^18",
            "@types/react-dom": "^18",
            "typescript": "^5",
            "autoprefixer": "^10.0.1",
            "postcss": "^8"
        }
    }, indent=2)
    write_file(out / "package.json", content)

# ─────────────────────────────────────────────
# TSCONFIG
# ─────────────────────────────────────────────

def gen_tsconfig(out: Path):
    content = json.dumps({
        "compilerOptions": {
            "target": "es5",
            "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True,
            "skipLibCheck": True,
            "strict": True,
            "noEmit": True,
            "esModuleInterop": True,
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "preserve",
            "incremental": True,
            "plugins": [{"name": "next"}],
            "paths": {"@/*": ["./*"]}
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"]
    }, indent=2)
    write_file(out / "tsconfig.json", content)

# ─────────────────────────────────────────────
# TAILWIND CONFIG
# ─────────────────────────────────────────────

def gen_tailwind_config(out: Path):
    content = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      colors: {
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        }
      }
    }
  },
  plugins: [],
}
"""
    write_file(out / "tailwind.config.js", content)

# ─────────────────────────────────────────────
# POSTCSS CONFIG
# ─────────────────────────────────────────────

def gen_postcss_config(out: Path):
    content = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
    write_file(out / "postcss.config.js", content)

# ─────────────────────────────────────────────
# NEXT CONFIG
# ─────────────────────────────────────────────

def gen_next_config(out: Path):
    content = """/** @type {import('next').NextConfig} */
const nextConfig = {}
module.exports = nextConfig
"""
    write_file(out / "next.config.js", content)

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────

def gen_global_css(out: Path):
    content = """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { box-sizing: border-box; }

body {
  background-color: #0a0a0f;
  color: #e2e8f0;
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

::selection { background: rgba(59, 130, 246, 0.3); color: #fff; }

@layer components {
  .card {
    @apply bg-slate-900 border border-slate-800 rounded-xl;
  }
  .badge {
    @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border;
  }
  .btn-primary {
    @apply px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200;
  }
  .btn-secondary {
    @apply px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg transition-colors duration-200 border border-slate-700;
  }
  .input {
    @apply w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200;
  }
  .table-row-hover {
    @apply hover:bg-slate-800/50 transition-colors duration-150;
  }
}
"""
    write_file(out / "app" / "globals.css", content)

# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────

def gen_layout(app_name: str, nav_items: list, out: Path):
    def get_nav_label(item) -> str:
        if isinstance(item, str):
            return item
        return item.get("label", str(item))

    def get_nav_path(item) -> str:
        if isinstance(item, str):
            return f"/{to_kebab_case(item)}"
        return item.get("path", f"/{to_kebab_case(item.get('label', 'page'))}")

    nav_links = "\n".join([
        f'          <a href="{get_nav_path(item)}" className="text-sm text-slate-400 hover:text-white transition-colors duration-200 px-3 py-1.5 rounded-lg hover:bg-slate-800">'
        f'{get_nav_label(item)}</a>'
        for item in nav_items
    ])

    first_letter = app_name[0].upper() if app_name else 'A'

    content = f"""import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{app_name}',
  description: 'Generated by AI App Compiler',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body className="bg-[#0a0a0f] text-slate-100 min-h-screen">

        <nav className="sticky top-0 z-50 border-b border-slate-800/60 bg-[#0a0a0f]/80 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
                  <span className="text-white text-xs font-bold">{first_letter}</span>
                </div>
                <span className="font-semibold text-white">{app_name}</span>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  AI Generated
                </span>
              </div>

              <div className="hidden md:flex items-center gap-1">
{nav_links}
              </div>

              <div className="flex items-center gap-3">
                <button className="text-sm text-slate-400 hover:text-white transition-colors">
                  Sign In
                </button>
                <button className="text-sm px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium">
                  Sign Up
                </button>
              </div>

            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {{children}}
        </main>

        <footer className="border-t border-slate-800 mt-16 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-sm text-slate-500">
                2024 {app_name}. Generated by AI App Compiler.
              </p>
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                Powered by Nvidia NIM
              </div>
            </div>
          </div>
        </footer>

      </body>
    </html>
  )
}}
"""
    write_file(out / "app" / "layout.tsx", content)

# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────

def gen_home_page(app_name: str, pages: list, out: Path):
    page_cards = "\n".join([
        f"""        <a href="{p.path}" className="group card p-6 hover:border-blue-500/50 hover:bg-slate-800/50 transition-all duration-300 block">
          <div className="flex items-start justify-between mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-lg font-bold">
              {p.name[0].upper() if p.name else 'P'}
            </div>
            <span className="{'bg-amber-500/10 text-amber-400 border-amber-500/20' if p.auth_required else 'bg-green-500/10 text-green-400 border-green-500/20'} inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border">
              {'Auth Required' if p.auth_required else 'Public'}
            </span>
          </div>
          <h2 className="text-base font-semibold text-white group-hover:text-blue-400 transition-colors mb-1">{p.title or p.name}</h2>
          <p className="text-sm text-slate-500">{p.path}</p>
          {f'<p className="text-xs text-slate-600 mt-2">{", ".join(p.roles_allowed)}</p>' if p.roles_allowed else ''}
        </a>"""
        for p in pages
    ])

    total_pages = len(pages)
    auth_pages = sum(1 for p in pages if p.auth_required)
    public_pages = sum(1 for p in pages if not p.auth_required)

    content = f""""use client"

export default function HomePage() {{
  return (
    <div>
      {{/* Hero */}}
      <div className="relative mb-12">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-transparent to-purple-600/10 rounded-2xl blur-3xl" />
        <div className="relative text-center py-16 px-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
            Generated by AI App Compiler Pipeline
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
            {app_name}
          </h1>
          <p className="text-lg text-slate-400 max-w-xl mx-auto">
            A fully structured application with auth, API, database schema, and business logic.
          </p>
          <div className="flex items-center justify-center gap-4 mt-8">
            <button className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200">
              Get Started
            </button>
            <button className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg transition-colors duration-200 border border-slate-700">
              View Docs
            </button>
          </div>
        </div>
      </div>

      {{/* Stats */}}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-blue-400">{total_pages}</p>
          <p className="text-xs text-slate-500 mt-1">Total Pages</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-amber-400">{auth_pages}</p>
          <p className="text-xs text-slate-500 mt-1">Auth Required</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">{public_pages}</p>
          <p className="text-xs text-slate-500 mt-1">Public Pages</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-blue-400">Live</p>
          <p className="text-xs text-slate-500 mt-1">Status</p>
        </div>
      </div>

      {{/* Pages Grid */}}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Application Pages</h2>
        <span className="text-sm text-slate-500">{total_pages} pages generated</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
{page_cards}
      </div>
    </div>
  )
}}
"""
    write_file(out / "app" / "page.tsx", content)

# ─────────────────────────────────────────────
# COMPONENT GENERATORS
# ─────────────────────────────────────────────

def gen_component_jsx(component) -> str:
    ctype = component.type.value if hasattr(component.type, 'value') else component.type
    label = component.label
    fields = [
        f if isinstance(f, str) else f.get("name", str(f))
        for f in component.fields
    ]
    actions = [
        a if isinstance(a, str) else a.get("label", str(a))
        for a in component.actions
    ]
    roles = component.visible_to_roles
    roles_str = ", ".join(roles) if roles else "all roles"
    data_source = component.data_source or "API"

    if ctype == "table":
        headers = "\n".join([
            f'                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">{f}</th>'
            for f in fields
        ]) if fields else '                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Column</th>'

        col_span = max(len(fields), 1) + 1

        return f"""      {{/* {label} — Table */}}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-white">{label}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Visible to: {roles_str}</p>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg transition-colors">Export</button>
            <button className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors">+ Add New</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-800/50">
              <tr>
{headers}
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td colSpan={{{col_span}}} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-2xl">📭</div>
                    <p className="text-slate-500 text-sm">No data yet</p>
                    <button className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors">Add First Record</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="px-6 py-3 border-t border-slate-800 flex items-center justify-between">
          <p className="text-xs text-slate-500">Showing 0 records</p>
          <div className="flex gap-1">
            <button className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-700 transition-colors">Prev</button>
            <button className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-700 transition-colors">Next</button>
          </div>
        </div>
      </div>"""

    elif ctype == "form":
        inputs = "\n".join([f"""        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">{f}</label>
          <input
            name="{f.lower().replace(' ', '_')}"
            placeholder="Enter {f.lower()}..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
          />
        </div>""" for f in fields]) if fields else """        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">Field</label>
          <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200" />
        </div>"""

        return f"""      {{/* {label} — Form */}}
      <div className="card p-6 max-w-2xl">
        <div className="mb-6">
          <h3 className="font-semibold text-white text-lg">{label}</h3>
          <p className="text-sm text-slate-500 mt-1">Fill in the details below</p>
        </div>
        <div className="space-y-4">
{inputs}
          <div className="flex gap-3 pt-2">
            <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200">
              Submit
            </button>
            <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg transition-colors duration-200 border border-slate-700">
              Cancel
            </button>
          </div>
        </div>
      </div>"""

    elif ctype == "chart":
        return f"""      {{/* {label} — Chart */}}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="font-semibold text-white">{label}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Live data from {data_source}</p>
          </div>
          <select className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option>Last 7 days</option>
            <option>Last 30 days</option>
            <option>Last 90 days</option>
          </select>
        </div>
        <div className="h-48 flex items-end gap-2 px-2">
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "40%"}}}}></div>
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "65%"}}}}></div>
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "45%"}}}}></div>
          <div className="flex-1 bg-blue-500/30 hover:bg-blue-500/50 rounded-t transition-colors border-t-2 border-blue-400" style={{{{height: "80%"}}}}></div>
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "55%"}}}}></div>
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "70%"}}}}></div>
          <div className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors" style={{{{height: "50%"}}}}></div>
        </div>
        <div className="flex justify-between mt-2 px-2">
          <span className="text-xs text-slate-500">Mon</span>
          <span className="text-xs text-slate-500">Tue</span>
          <span className="text-xs text-slate-500">Wed</span>
          <span className="text-xs text-slate-500">Thu</span>
          <span className="text-xs text-slate-500">Fri</span>
          <span className="text-xs text-slate-500">Sat</span>
          <span className="text-xs text-slate-500">Sun</span>
        </div>
      </div>"""

    elif ctype == "card":
        return f"""      {{/* {label} — Stat Card */}}
      <div className="card p-6 hover:border-blue-500/30 transition-colors group">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-slate-400">{label}</p>
            <p className="text-3xl font-bold text-white mt-1 group-hover:text-blue-400 transition-colors">—</p>
            <p className="text-xs text-slate-500 mt-1">Live from {data_source}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-xl">
            📊
          </div>
        </div>
      </div>"""

    elif ctype == "list":
        return f"""      {{/* {label} — List */}}
      <div className="card divide-y divide-slate-800">
        <div className="px-6 py-4 flex items-center justify-between">
          <h3 className="font-semibold text-white">{label}</h3>
          <button className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors">+ Add</button>
        </div>
        <div className="px-6 py-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm text-slate-300">1</div>
            <div>
              <p className="text-sm font-medium text-white">Sample Item</p>
              <p className="text-xs text-slate-500">Description here</p>
            </div>
          </div>
          <button className="text-xs text-slate-500 hover:text-white transition-colors">View</button>
        </div>
        <div className="px-6 py-8 text-center">
          <p className="text-slate-500 text-sm">No more items</p>
        </div>
      </div>"""

    elif ctype == "modal":
        return f"""      {{/* {label} — Modal Trigger */}}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-white">{label}</h3>
            <p className="text-sm text-slate-500 mt-1">Click to open modal</p>
          </div>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200">
            Open
          </button>
        </div>
      </div>"""

    else:
        return f"""      {{/* {label} — {ctype} */}}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            ⚡
          </div>
          <h3 className="font-semibold text-white">{label}</h3>
        </div>
        <p className="text-sm text-slate-500">Component: {ctype} — connect to {data_source}</p>
      </div>"""

# ─────────────────────────────────────────────
# UI PAGE GENERATOR
# ─────────────────────────────────────────────

def gen_ui_page(page, out: Path):
    components_jsx = "\n\n".join([gen_component_jsx(c) for c in page.components])
    roles_str = ", ".join(page.roles_allowed) if page.roles_allowed else "All roles"
    is_auth = page.auth_required
    page_title = page.title or page.name

    content = f""""use client"

export default function {to_pascal_case(page.name)}Page() {{
  return (
    <div>
      {{/* Page Header */}}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-white">{page_title}</h1>
            <span className="{'bg-amber-500/10 text-amber-400 border-amber-500/20' if is_auth else 'bg-green-500/10 text-green-400 border-green-500/20'} inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border">
              {'Auth Required' if is_auth else 'Public'}
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Roles: <span className="text-slate-400">{roles_str}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg transition-colors duration-200 border border-slate-700 text-sm">
            Export
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 text-sm">
            + New
          </button>
        </div>
      </div>

      {{/* Components */}}
      <div className="space-y-6">
{components_jsx}
      </div>
    </div>
  )
}}
"""
    route = page.path.strip("/")
    if not route:
        route = "home"
    write_file(out / "app" / route / "page.tsx", content)

# ─────────────────────────────────────────────
# API ROUTES GENERATOR
# ─────────────────────────────────────────────

def gen_api_route(endpoint, out: Path):
    method = endpoint.method.value if hasattr(endpoint.method, 'value') else endpoint.method
    roles = endpoint.roles_allowed
    roles_str = ", ".join(roles) if roles else "all"

    content = f"""import {{ NextRequest, NextResponse }} from 'next/server'

/**
 * {endpoint.description}
 * Auth required: {endpoint.auth_required}
 * Roles: {roles_str}
 */

export async function {method}(request: NextRequest) {{
  try {{
    // TODO: Verify JWT token
    // TODO: Check role permissions: {roles_str}

    const data = {{
      message: "{endpoint.description}",
      path: "{endpoint.path}",
      method: "{method}",
      timestamp: new Date().toISOString(),
      status: "scaffold"
    }}

    return NextResponse.json({{ success: true, data }}, {{ status: 200 }})

  }} catch (error) {{
    return NextResponse.json(
      {{ success: false, error: "Internal server error" }},
      {{ status: 500 }}
    )
  }}
}}
"""
    clean_path = (
        endpoint.path
        .replace(":", "")
        .replace("{", "")
        .replace("}", "")
        .strip("/")
    )
    route_path = clean_path.split("/")
    file_path = out / "app" / Path(*route_path) / "route.ts"
    write_file(file_path, content)

# ─────────────────────────────────────────────
# DB DOCS
# ─────────────────────────────────────────────

def gen_db_docs(db_schema, out: Path):
    lines = ["# Database Schema\n\n", "Generated by AI App Compiler Pipeline\n\n"]
    for table in db_schema.tables:
        lines.append(f"## Table: `{table.name}`\n\n")
        lines.append("| Field | Type | Required | Primary Key | Foreign Key |\n")
        lines.append("|-------|------|----------|-------------|-------------|\n")
        for field in table.fields:
            fk = field.foreign_key or "—"
            ft = field.type.value if hasattr(field.type, 'value') else field.type
            lines.append(f"| {field.name} | {ft} | {field.required} | {field.primary_key} | {fk} |\n")
        if table.relations:
            lines.append(f"\n**Relations:** {', '.join([str(r) for r in table.relations])}\n")
        lines.append("\n")
    write_file(out / "docs" / "database.md", "".join(lines))

# ─────────────────────────────────────────────
# AUTH DOCS
# ─────────────────────────────────────────────

def gen_auth_docs(auth_schema, out: Path):
    lines = ["# Auth & Permissions\n\n"]
    lines.append(f"- JWT Enabled: {auth_schema.jwt_enabled}\n")
    lines.append(f"- Session Timeout: {auth_schema.session_timeout_minutes} minutes\n")
    lines.append(f"- OAuth Providers: {', '.join(auth_schema.oauth_providers) or 'None'}\n\n")
    for role in auth_schema.roles:
        lines.append(f"## Role: `{role.role}`\n\n")
        lines.append(f"- Premium Access: {role.can_access_premium}\n\n")
        lines.append("| Resource | Actions |\n|----------|----------|\n")
        for perm in role.permissions:
            lines.append(f"| {perm.resource} | {', '.join(perm.actions)} |\n")
        lines.append("\n")
    write_file(out / "docs" / "auth.md", "".join(lines))

# ─────────────────────────────────────────────
# APP CONFIG DUMP
# ─────────────────────────────────────────────

def gen_app_config_json(config: AppConfig, out: Path):
    write_file(
        out / "app-config.json",
        json.dumps(config.model_dump(), indent=2, default=str)
    )

# ─────────────────────────────────────────────
# README
# ─────────────────────────────────────────────

def gen_readme(config: AppConfig, out: Path):
    app_name = config.intent.app_name
    tables_list = "\n".join([f"- **{t.name}** — {len(t.fields)} fields" for t in config.database.tables])
    endpoints_list = "\n".join([
        f"- `{e.method.value if hasattr(e.method, 'value') else e.method} {e.path}` — {e.description}"
        for e in config.api.endpoints[:8]
    ])
    roles_list = "\n".join([
        f"- **{r.role}**" + (" (Premium)" if r.can_access_premium else "")
        for r in config.auth.roles
    ])
    pages_list = "".join([
        f"├── {p.path.strip('/')}/page.tsx\n" for p in config.ui.pages[:5]
    ])

    content = f"""# {app_name}

> Generated by AI App Compiler — Natural Language to Structured App

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Structure

app/
├── page.tsx
{pages_list}└── api/v1/...
docs/
├── database.md
└── auth.md
app-config.json

## Database Tables

{tables_list}

## API Endpoints

{endpoints_list}

## Roles

{roles_list}

## Generated By

- Pipeline: 4-stage AI compiler
- Model: meta/llama-3.3-70b-instruct via Nvidia NIM
- Validation: Pydantic v2 with cross-layer consistency checks
"""
    write_file(out / "README.md", content)

# ─────────────────────────────────────────────
# MASTER GENERATOR
# ─────────────────────────────────────────────

def generate_app(config: AppConfig, output_dir: str = "generated_app") -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    app_name = config.intent.app_name
    logger.info(f"Generating app: {app_name} → {out.resolve()}")

    # Project config files
    gen_package_json(app_name, out)
    gen_tsconfig(out)
    gen_tailwind_config(out)
    gen_postcss_config(out)
    gen_next_config(out)
    gen_global_css(out)

    # Layout + Home
    gen_layout(app_name, config.ui.nav_items, out)
    gen_home_page(app_name, config.ui.pages, out)

    # UI Pages
    for page in config.ui.pages:
        gen_ui_page(page, out)
        logger.info(f"Generated page: {page.path}")

    # API Routes
    for endpoint in config.api.endpoints:
        gen_api_route(endpoint, out)

    # Docs + Config + README
    gen_db_docs(config.database, out)
    gen_auth_docs(config.auth, out)
    gen_app_config_json(config, out)
    gen_readme(config, out)

    logger.info(f"App generation complete: {out.resolve()}")
    return str(out.resolve())


# ─────────────────────────────────────────────
# LOCAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO)

    from pipeline.stage1_intent import run_stage1
    from pipeline.stage2_design import run_stage2
    from pipeline.stage3_schema import run_stage3
    from pipeline.stage4_refine import run_stage4

    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    intent = run_stage1(test_prompt)
    design = run_stage2(intent)
    db, api, ui, auth, biz = run_stage3(intent, design)
    final = run_stage4(intent, design, db, api, ui, auth, biz)

    output_path = generate_app(final, output_dir="generated_app")
    print(f"\n✅ App generated at: {output_path}")