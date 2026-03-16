import { useEffect, useRef, useState } from 'react'
import { fetchBootTime } from '../api/client'

const POLL_INTERVAL_MS = 5_000

export default function ServerHealthMonitor() {
  const bootTimeRef = useRef<number | null>(null)
  const [restarted, setRestarted] = useState(false)

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>

    const check = async () => {
      try {
        const bootTime = await fetchBootTime()
        if (bootTimeRef.current === null) {
          // First check — record the boot time
          bootTimeRef.current = bootTime
        } else if (bootTime !== bootTimeRef.current) {
          // Boot time changed — server restarted
          bootTimeRef.current = bootTime
          setRestarted(true)
        }
      } catch {
        // Server unreachable — will detect restart on next successful poll
      }
    }

    check()
    timer = setInterval(check, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [])

  if (!restarted) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-white px-4 py-2 text-center text-sm shadow-lg flex items-center justify-center gap-3">
      <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
      <span>
        服务器已重启，之前正在运行的任务已中断。请刷新页面查看最新状态。
      </span>
      <button
        onClick={() => window.location.reload()}
        className="bg-white text-amber-700 px-3 py-1 rounded text-xs font-medium hover:bg-amber-50 transition-colors"
      >
        刷新页面
      </button>
      <button
        onClick={() => setRestarted(false)}
        className="text-white/80 hover:text-white ml-1"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  )
}
