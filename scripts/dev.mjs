// One command for the whole project: `npm run setup` once, then `npm run dev`. No dependencies.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'

const win = process.platform === 'win32'
const venvPython = resolve('backend', '.venv', win ? join('Scripts', 'python.exe') : join('bin', 'python'))
// Windows needs a shell to run npm.cmd, but a shell would mangle the python path, so use it for npm only.
const opts = cmd => ({ stdio: 'inherit', shell: win && cmd === 'npm' })

function step(label, cmd, args, cwd = '.') {
  console.log(`\n> ${label}`)
  const r = spawnSync(cmd, args, { ...opts(cmd), cwd })
  if (r.status !== 0) { console.error(`Failed: ${label}`); process.exit(r.status ?? 1) }
}

const mode = process.argv[2]

if (mode === 'setup') {
  if (!existsSync(venvPython)) step('Create Python environment', win ? 'python' : 'python3', ['-m', 'venv', 'backend/.venv'])
  step('Install backend packages', venvPython, ['-m', 'pip', 'install', '-q', '-r', 'backend/requirements.txt'])
  step('Install dashboard packages', 'npm', ['ci'], 'frontend')
  console.log('\nReady. Run: npm run dev')
} else if (!existsSync(venvPython) || !existsSync('frontend/node_modules')) {
  console.error('First run `npm run setup`.')
  process.exit(1)
} else if (mode === 'test') {
  step('Backend tests', venvPython, ['-m', 'pytest', '-q'], 'backend')
} else {
  const procs = [
    spawn(venvPython, ['-m', 'uvicorn', 'app.main:app', '--port', '8000', '--app-dir', 'backend'], opts(venvPython)),
    spawn('npm', ['run', 'dev', '--', '--port', '5173'], { ...opts('npm'), cwd: 'frontend' }),
  ]
  console.log('\nAPI on http://localhost:8000 · dashboard on http://localhost:5173 (Ctrl+C stops both)\n')
  // On Windows npm runs inside cmd.exe, so kill the whole process tree or Vite keeps port 5173.
  const kill = p => (win ? spawnSync('taskkill', ['/pid', String(p.pid), '/T', '/F'], { stdio: 'ignore' }) : p.kill())
  const stop = () => { procs.forEach(kill); process.exit() }
  process.on('SIGINT', stop)
  procs.forEach(p => p.on('exit', code => { if (code) { console.error('A server stopped; shutting down.'); stop() } }))
}
