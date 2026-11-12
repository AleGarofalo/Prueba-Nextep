import { Globe } from 'lucide-react'

// SVGs keep the common supplier flags legible on Windows, where flag emoji
// render as two regional-indicator letters instead of a flag.
export function CountryFlag({ code }: { code: string }) {
  const props = { width: 18, height: 12, viewBox: '0 0 30 20', 'aria-hidden': true as const, style: { display: 'inline-block', verticalAlign: '-1px', borderRadius: 2, flexShrink: 0 } }
  switch (code) {
    case 'ES': return <svg {...props}><path fill="#AA151B" d="M0 0h30v20H0z" /><path fill="#F1BF00" d="M0 5h30v10H0z" /></svg>
    case 'AR': return <svg {...props}><path fill="#75AADB" d="M0 0h30v20H0z" /><path fill="#fff" d="M0 6.67h30v6.66H0z" /><circle fill="#F6B40E" cx="15" cy="10" r="2" /></svg>
    case 'MX': return <svg {...props}><path fill="#fff" d="M0 0h30v20H0z" /><path fill="#006847" d="M0 0h10v20H0z" /><path fill="#CE1126" d="M20 0h10v20H20z" /><circle fill="#8E6F3E" cx="15" cy="10" r="2" /></svg>
    case 'US': return <svg {...props}><path fill="#fff" d="M0 0h30v20H0z" />{Array.from({ length: 7 }, (_, i) => <path key={i} fill="#B22234" d={`M0 ${i * 40 / 13}h30v${20 / 13}H0z`} />)}<path fill="#3C3B6E" d="M0 0h13v10.77H0z" />{Array.from({ length: 9 }, (_, row) => Array.from({ length: row % 2 ? 5 : 6 }, (_, col) => <circle key={`${row}-${col}`} fill="#fff" cx={1.1 + col * 2.15 + (row % 2 ? 1.07 : 0)} cy={1 + row * 1.09} r=".35" />))}</svg>
    case 'GB': return <svg {...props}><path fill="#012169" d="M0 0h30v20H0z" /><path stroke="#fff" strokeWidth="4" d="m0 0 30 20M30 0 0 20" /><path stroke="#C8102E" strokeWidth="1.6" d="m0 0 30 20M30 0 0 20" /><path stroke="#fff" strokeWidth="7" d="M15 0v20M0 10h30" /><path stroke="#C8102E" strokeWidth="4" d="M15 0v20M0 10h30" /></svg>
    default: return <Globe size={14} aria-hidden="true" style={{ verticalAlign: '-2px' }} />
  }
}
