
import { createContext, useContext, useEffect, useRef, useState } from 'react'

import type { CSSProperties, ReactNode } from 'react'

import { motion, useInView } from 'framer-motion'

const logoS = 'https://qclay.design/lovable/kraken/dashboard-logo-s.svg'

const tmMark = 'https://qclay.design/lovable/kraken/dashboard-tm.svg'

const bellIcon = 'https://qclay.design/lovable/kraken/dashboard-bell.svg'

const userIcon = 'https://qclay.design/lovable/kraken/dashboard-user.svg'

const favChartIcon = 'https://qclay.design/lovable/kraken/dashboard-fav-chart.svg'

const calendarIcon = 'https://qclay.design/lovable/kraken/dashboard-calendar.svg'

const importIcon = 'https://qclay.design/lovable/kraken/dashboard-import.svg'

const chartBars = 'https://qclay.design/lovable/kraken/dashboard-chart-bars.svg'

const chartLine = 'https://qclay.design/lovable/kraken/dashboard-chart-line.svg'

const CANVAS_WIDTH = 948

const CANVAS_HEIGHT = 718.4

const MUTED = '#999ba8'

const ACCENT = '#ff6215'

const HAIRLINE = 'rgba(0,0,0,0.1)'

const EASE = [0.22, 1, 0.36, 1] as const

const ActiveContext = createContext(false)

const useActive = () => useContext(ActiveContext)

/* ---------- animated primitives ---------- */

type TextProps = {

x: number

y: number

w: number

h: number

size: number

lh: number

color?: string

weight?: number

ls?: number

align?: 'left' | 'center' | 'right'

vTop?: boolean

underline?: boolean

uppercase?: boolean

delay?: number

children: ReactNode

}

function T({

x,

y,

w,

h,

size,

lh,

color = '#000',

weight = 500,

ls = -0.1,

align = 'left',

vTop,

underline,

uppercase,

delay,

children,

}: TextProps) {

const active = useActive()

const style: CSSProperties = {

left: x,

top: y,

width: w,

height: h,

alignItems: vTop ? 'flex-start' : 'center',

justifyContent: align === 'left' ? 'flex-start' : align === 'center' ? 'center' : 'flex-end',

fontSize: size,

lineHeight: `${lh}px`,

letterSpacing: `${ls}px`,

fontWeight: weight,

color,

textTransform: uppercase ? 'uppercase' : undefined,

textDecoration: underline ? 'underline' : undefined,

textUnderlineOffset: underline ? 2 : undefined,

}

if (delay === undefined) {

return (

<div className="absolute flex whitespace-nowrap" style={style}>

{children}

</div>

)

}

return (

<motion.div

className="absolute flex whitespace-nowrap"

style={style}

initial={{ opacity: 0, y: 4 }}

animate={active ? { opacity: 1, y: 0 } : undefined}

transition={{ duration: 0.5, delay, ease: EASE }}

>

{children}

</motion.div>

)

}

function Box({ style, className = '' }: { style: CSSProperties; className?: string }) {

return <div className={`absolute ${className}`} style={style} />

}

/** Grows from its centre outwards — horizontal by default, vertical when `vertical`. */

function Line({

x,

y,

w,

h,

delay = 0,

vertical,

background = HAIRLINE,

}: {

x: number

y: number

w: number

h: number

delay?: number

vertical?: boolean

background?: string

}) {

const active = useActive()

const axis = vertical ? 'scaleY' : 'scaleX'

return (

<motion.div

className="absolute"

style={{ left: x, top: y, width: w, height: h, background }}

initial={{ [axis]: 0 }}

animate={active ? { [axis]: 1 } : undefined}

transition={{ duration: 0.7, delay, ease: EASE }}

/>

)

}

/** Scales up from nothing — used for pills, badges and icon buttons. */

function Pop({

x,

y,

w,

h,

delay = 0,

background,

border,

origin,

radius,

children,

}: {

x: number

y: number

w: number

h: number

delay?: number

background?: string

border?: string

origin?: string

radius?: number

children?: ReactNode

}) {

const active = useActive()

return (

<motion.div

className="absolute"

style={{

left: x,

top: y,

width: w,

height: h,

background,

border,

borderRadius: radius,

transformOrigin: origin,

}}

initial={{ scale: 0 }}

animate={active ? { scale: 1 } : undefined}

transition={{ duration: 0.5, delay, ease: [0.34, 1.4, 0.64, 1] }}

>

{children}

</motion.div>

)

}

/**

* Counts up to `value`, keeping its exact formatting: only the digits are

* animated, every separator stays where the design put it.

*/

function CountUp({ value, delay = 0, duration = 1.3 }: { value: string; delay?: number; duration?: number }) {

const active = useActive()

const digits = value.replace(/\D/g, '')

const [shown, setShown] = useState(0)

useEffect(() => {

if (!active || !digits) return

const end = Number(digits)

const startAt = performance.now() + delay * 1000

let frame = 0

const tick = (now: number) => {

const t = Math.min(Math.max((now - startAt) / (duration * 1000), 0), 1)

setShown(Math.round(end * (1 - Math.pow(1 - t, 3))))

if (t < 1) frame = requestAnimationFrame(tick)

}

frame = requestAnimationFrame(tick)

return () => cancelAnimationFrame(frame)

}, [active, digits, delay, duration])

if (!digits) return <>{value}</>

const padded = String(shown).padStart(digits.length, '0')

let i = 0

const text = value.replace(/\d/g, () => padded[i++])

return <>{text}</>

}

function Icon({ src, x, y, size }: { src: string; x: number; y: number; size: number }) {

return <img src={src} alt="" className="absolute" style={{ left: x, top: y, width: size, height: size }} />

}

function Caret({ x, y, w, h, color }: { x: number; y: number; w: number; h: number; color: string }) {

return (

<svg className="absolute" style={{ left: x, top: y }} width={w} height={h} viewBox="0 0 7 7" fill="none">

<path

d="M4.9 2.8L3.5 4.2L2.1 2.8"

stroke={color}

strokeWidth="0.79"

strokeLinecap="round"

strokeLinejoin="round"

/>

</svg>

)

}

/* ---------- nav ---------- */

const navLinks: { label: string; x: number; w: number; active?: boolean }[] = [

{ label: 'My Portfolio', x: 56, w: 46, active: true },

{ label: 'Overview', x: 115.2, w: 37 },

{ label: 'Top Traders', x: 165.3, w: 46 },

{ label: 'My Copy Traders', x: 224.5, w: 65 },

{ label: 'My Favorites', x: 302.7, w: 49 },

]

function NavBar() {

return (

<>

<Box style={{ left: 0, top: 0, width: CANVAS_WIDTH, height: 34, background: '#000' }} />

<Box

style={{

left: 0,

top: 0,

width: 36.8,

height: 34,

background: 'linear-gradient(180deg, #FF6215 0%, #FFF28E 100%)',

}}

/>

<img src={logoS} alt="" className="absolute" style={{ left: 11.5, top: 12.6, width: 11.5, height: 9.9 }} />

<img src={tmMark} alt="" className="absolute" style={{ left: 24.2, top: 9.3, width: 3.8, height: 2.2 }} />

{navLinks.map((link, i) => (

<T

key={link.label}

x={link.x}

y={9.3}

w={link.w}

h={13}

size={8.78}

lh={12.9}

color={link.active ? '#fff' : 'rgba(255,255,255,0.5)'}

underline={link.active}

delay={0.05 + i * 0.05}

>

{link.label}

</T>

))}

<T x={438.6} y={8.8} w={176.2} h={13} size={8.78} lh={12.9} color="rgba(255,255,255,0.5)" delay={0.3}>

Search Pair...

</T>

<Line x={438.6} y={26.2} w={176.2} h={0.82} background="rgba(255,255,255,0.4)" delay={0.3} />

<Pop

x={693.3}

y={7.7}

w={18.7}

h={18.7}

delay={0.4}

background="rgba(255,255,255,0.15)"

border="0.55px solid rgba(255,255,255,0.2)"

>

<Icon src={bellIcon} x={4.9} y={5} size={8.8} />

</Pop>

<Pop

x={714.2}

y={7.7}

w={18.7}

h={18.7}

delay={0.45}

background="rgba(255,255,255,0.15)"

border="0.55px solid rgba(255,255,255,0.2)"

>

<Icon src={userIcon} x={4.9} y={5} size={8.8} />

</Pop>

<Pop x={755.3} y={7.7} w={24.6} h={9.4} delay={0.5} background="#fff">

<T x={3.3} y={2.2} w={18} h={5} size={6.59} lh={9.7} weight={400}>

Demo

</T>

</Pop>

<T x={783.2} y={9.9} w={29} h={5} size={6.59} lh={9.7} weight={400} color="rgba(255,255,255,0.4)" delay={0.5}>

Total value

</T>

<T x={755.3} y={20.6} w={55} h={5} size={7.69} lh={10} color="#fff" uppercase delay={0.55}>

<CountUp value="10,000.00" delay={0.55} />

<span style={{ color: 'rgba(255,255,255,0.4)' }}>&nbsp;USDC</span>

</T>

<Caret x={812.5} y={19.8} w={6.6} h={6.6} color="rgba(255,255,255,0.7)" />

<Pop x={841.5} y={7.7} w={89.6} h={18.7} delay={0.6} background="rgba(255,255,255,0.15)">

<T x={4.9} y={3.8} w={66} h={11} size={7.69} lh={11.3} ls={-0.08} weight={400} color="#fff" align="center" uppercase>

Connect wallet

</T>

<Box style={{ left: 74.8, top: 1.1, width: 0.55, height: 16.5, background: 'rgba(255,255,255,0.17)' }} />

<svg className="absolute" style={{ left: 78.6, top: 6.3 }} width={6} height={6} viewBox="0 0 6 6" fill="none">

<path

d="M2.3 1.1L4.1 3L2.3 4.9"

stroke="#fff"

strokeWidth="1.13"

strokeLinecap="round"

strokeLinejoin="round"

/>

</svg>

</Pop>

</>

)

}

/* ---------- header ---------- */

function Header() {

return (

<>

<img src={favChartIcon} alt="" className="absolute" style={{ left: 17.6, top: 46.7, width: 13.2, height: 13.2 }} />

<T x={37.3} y={48.7} w={69} h={9} size={13.17} lh={19.4} delay={0.15}>

My Portfolio

</T>

<Pop x={787.2} y={48.3} w={91.9} h={17.4} delay={0.25} background="#eeeeee">

<Icon src={calendarIcon} x={4.4} y={4.3} size={8.8} />

<T x={18.6} y={2.2} w={54} h={13} size={8.78} lh={12.9}>

May 1 - May 31

</T>

<Caret x={78.1} y={4.3} w={9.3} h={8.8} color="rgba(0,0,0,0.4)" />

</Pop>

<Pop x={881.6} y={48.3} w={49.1} h={17.4} delay={0.3} background="#eeeeee">

<Icon src={importIcon} x={4.4} y={4.3} size={8.8} />

<T x={18.6} y={2.2} w={26} h={13} size={8.78} lh={12.9}>

Export

</T>

</Pop>

</>

)

}

/* ---------- portfolio value ---------- */

function PortfolioValue() {

return (

<>

<T x={18.7} y={91.7} w={62} h={15} size={9.88} lh={14.5} color={MUTED} delay={0.35}>

Portfolio Value

</T>

<T x={17.6} y={120.8} w={370} h={74} size={76.85} lh={73.8} ls={-2.31} weight={400} align="center" vTop delay={0.4}>

<CountUp value="$12,486.075" delay={0.45} duration={1.5} />

</T>

<T x={401.2} y={175.8} w={34} h={19} size={13.17} lh={19.4} color={MUTED} delay={0.6}>

USDT

</T>

</>

)

}

/* ---------- statistics ---------- */

const years: { label: string; x: number; w: number; active?: boolean }[] = [

{ label: '2024', x: 523.1, w: 25, active: true },

{ label: '2025', x: 558, w: 25 },

{ label: '2026', x: 592.9, w: 26 },

]

const stats = [

{

label: 'Total P&L',

x: 523.1,

labelW: 112.3,

value: '$1,246.75',

valueW: 71,

badge: '+11.09%',

badgeX: 606.6,

badgeW: 35.8,

badgeTextW: 27,

},

{

label: 'ROI',

x: 669,

labelW: 105.4,

value: '+18.42%',

valueW: 65,

badge: '+2.8%',

badgeX: 746.5,

badgeW: 29.8,

badgeTextW: 21,

},

{

label: 'Total Invested',

x: 808.1,

labelW: 121.3,

value: '$11,240.00',

valueW: 81,

badge: '+8.02%',

badgeX: 901.6,

badgeW: 34.8,

badgeTextW: 26,

},

]

function Statistics() {

return (

<>

<T x={523.1} y={91.7} w={39} h={15} size={9.88} lh={14.5} color={MUTED} delay={0.35}>

Statistics

</T>

{years.map((year, i) => (

<T

key={year.label}

x={year.x}

y={113.1}

w={year.w}

h={16}

size={10.98}

lh={16.1}

color={year.active ? '#000' : 'rgba(0,0,0,0.4)'}

underline={year.active}

delay={0.4 + i * 0.05}

>

{year.label}

</T>

))}

{stats.map((stat, i) => {

const delay = 0.55 + i * 0.1

return (

<div key={stat.label}>

<T x={stat.x} y={151} w={stat.labelW} h={13} size={8.78} lh={12.9} color="rgba(0,0,0,0.3)" delay={delay}>

{stat.label}

</T>

<T x={stat.x} y={165.1} w={stat.valueW} h={26} size={17.57} lh={25.8} delay={delay + 0.05}>

<CountUp value={stat.value} delay={delay + 0.1} />

</T>

<Pop x={stat.badgeX} y={172.6} w={stat.badgeW} h={11} delay={delay + 0.2} background={ACCENT}>

<T x={4.4} y={0} w={stat.badgeTextW} h={11} size={7.69} lh={11.3} color="#fff">

<CountUp value={stat.badge} delay={delay + 0.25} duration={0.9} />

</T>

</Pop>

</div>

)

})}

<Line x={652.2} y={151} w={0.55} h={40.1} vertical delay={0.6} />

<Line x={791.2} y={151} w={0.55} h={40.1} vertical delay={0.65} />

</>

)

}

/* ---------- value chart ---------- */

const ranges = [

{ label: 'All', active: true },

{ label: '1H' },

{ label: '1D' },

{ label: '1W' },

{ label: '1Y' },

]

const axisLabels = [

{ label: '$32.0K', y: 290.9 },

{ label: '$31.8K', y: 311.5 },

{ label: '$31.6K', y: 332 },

{ label: '$31.4K', y: 352.6 },

{ label: '$31.2K', y: 373.2 },

]

const timeLabels = [

{ label: '4:00 PM', x: 17, w: 24 },

{ label: '6:00 PM', x: 66.5, w: 24 },

{ label: '8:00 PM', x: 116, w: 24 },

{ label: '12:00 PM', x: 165.1, w: 26 },

{ label: '4:00 AM', x: 216.3, w: 24 },

{ label: '6:00 AM', x: 265.8, w: 24 },

{ label: '8:00 AM', x: 315.3, w: 24 },

{ label: '10:00 AM', x: 364.7, w: 27 },

{ label: '12:00 AM', x: 416.9, w: 27 },

]

function ValueChart() {

const active = useActive()

return (

<>

<T x={17} y={245.9} w={123.1} h={15} size={9.88} lh={14.5} color={MUTED} delay={0.7}>

Value Chart

</T>

<T x={17} y={263.1} w={57} h={19} size={13.17} lh={19.4} delay={0.75}>

<CountUp value="$2,246.24" delay={0.8} duration={1.1} />

</T>

{ranges.map((range, i) => (

<Pop

key={range.label}

x={329.7 + i * 27.45}

y={261.3}

w={25.3}

h={15.4}

delay={0.8 + i * 0.06}

background={range.active ? '#000' : '#eeeeee'}

>

<T x={0} y={0} w={25.3} h={15.4} size={8.78} lh={12.9} align="center" color={range.active ? '#fff' : '#000'}>

{range.label}

</T>

</Pop>

))}

{/* bars + line reveal together, left to right */}

<motion.div

className="absolute overflow-hidden"

style={{ left: 17, top: 307.37, width: 427.5, height: 71.1 }}

initial={{ clipPath: 'inset(0 100% 0 0)' }}

animate={active ? { clipPath: 'inset(0 0% 0 0)' } : undefined}

transition={{ duration: 1.3, delay: 0.95, ease: 'easeInOut' }}

>

<img src={chartBars} alt="" className="absolute" style={{ left: 0, top: 0, width: 426.74, height: 70.81 }} />

<img src={chartLine} alt="" className="absolute" style={{ left: 0.6, top: 23.03, width: 427, height: 49 }} />

</motion.div>

{timeLabels.map((time, i) => (

<T

key={time.label}

x={time.x}

y={386.5}

w={time.w}

h={5}

size={6.59}

lh={7.9}

vTop

color="rgba(0,0,0,0.3)"

delay={1.1 + i * 0.03}

>

{time.label}

</T>

))}

{axisLabels.map((axis, i) => (

<T

key={axis.label}

x={453.2}

y={axis.y}

w={30.9}

h={5}

size={6.59}

lh={7.9}

align="right"

vTop

color="rgba(0,0,0,0.4)"

delay={1 + i * 0.05}

>

{axis.label}

</T>

))}

</>

)

}

/* ---------- allocation ---------- */

const allocations = [

{

symbol: 'ETH',

symbolX: 523.1,

symbolW: 17,

name: 'Ethereum',

nameX: 544.5,

nameW: 28,

price: '$ 3832,26',

priceX: 623.2,

priceW: 30,

headerY: 319.5,

box: { x: 523.1, y: 336.3, w: 130.1, h: 50.5 },

accent: '#000',

delay: 1.05,

},

{

symbol: 'BTC',

symbolX: 661.5,

symbolW: 17,

name: 'Bitcoin',

nameX: 682.9,

nameW: 20,

price: '$ 6,612,02',

priceX: 763.1,

priceW: 29,

headerY: 275,

box: { x: 661.5, y: 291.3, w: 130.6, h: 96.1 },

accent: ACCENT,

delay: 1.15,

},

{

symbol: 'USDT',

symbolX: 800.9,

symbolW: 23,

name: 'Teher',

nameX: 828.3,

nameW: 17,

price: '$ 0,612,02',

priceX: 902,

priceW: 29,

headerY: 361.2,

box: { x: 800.9, y: 378, w: 130.1, h: 8.8 },

accent: '#000',

delay: 1.25,

},

]

const HATCH = 'repeating-linear-gradient(337.3deg, rgba(0,0,0,0.1) 0 0.55px, rgba(0,0,0,0) 0.55px 2.03px)'

function Allocation() {

const active = useActive()

return (

<>

<T x={523.7} y={252} w={46} h={16} size={10.98} lh={16.1} underline delay={0.7}>

Alocation

</T>

<T x={579.6} y={252} w={33} h={16} size={10.98} lh={16.1} color="rgba(0,0,0,0.4)" delay={0.75}>

Charts

</T>

{[657.6, 796.5].map((x, i) => (

<Line

key={x}

x={x}

y={304.1}

w={0.55}

h={82.9}

vertical

delay={1 + i * 0.08}

background={`repeating-linear-gradient(to bottom, ${HAIRLINE} 0 2.2px, rgba(0,0,0,0) 2.2px 4.4px)`}

/>

))}

{allocations.map((coin) => (

<div key={coin.symbol}>

<T x={coin.symbolX} y={coin.headerY} w={coin.symbolW} h={13} size={8.78} lh={12.9} weight={700} delay={coin.delay}>

{coin.symbol}

</T>

<T

x={coin.nameX}

y={coin.headerY + 1.5}

w={coin.nameW}

h={10}

size={6.59}

lh={9.7}

color="rgba(0,0,0,0.4)"

delay={coin.delay + 0.05}

>

{coin.name}

</T>

<T

x={coin.priceX}

y={coin.headerY + 1.5}

w={coin.priceW}

h={10}

size={6.59}

lh={9.7}

align="right"

delay={coin.delay + 0.05}

>

<CountUp value={coin.price} delay={coin.delay + 0.1} duration={1} />

</T>

<motion.div

className="absolute"

style={{

left: coin.box.x,

top: coin.box.y,

width: coin.box.w,

height: coin.box.h,

boxSizing: 'border-box',

borderTop: `2px solid ${coin.accent}`,

backgroundColor: 'rgba(238,238,238,0.3)',

backgroundImage: HATCH,

transformOrigin: 'bottom',

}}

initial={{ scaleY: 0 }}

animate={active ? { scaleY: 1 } : undefined}

transition={{ duration: 0.7, delay: coin.delay, ease: EASE }}

/>

</div>

))}

</>

)

}

/* ---------- open positions ---------- */

const positionTabs = [

{ label: 'Open Positions', x: 17, w: 66.8, textW: 58, active: true },

{ label: 'Trade History', x: 88.2, w: 59.8, textW: 51 },

{ label: 'Analitics', x: 152.4, w: 41.8, textW: 33 },

]

const positionColumns = [

{ label: 'Crypto', x: 17, y: 450, w: 23 },

{ label: 'P&L (%)', x: 128.4, y: 450.5, w: 26, caret: { x: 155.5, y: 452.7 } },

{ label: 'Risk', x: 268.4, y: 450, w: 15 },

{ label: 'P&L (%)', x: 377.1, y: 448.9, w: 26, caret: { x: 404.2, y: 451.1 } },

{ label: 'P&L (%)', x: 551.7, y: 450, w: 26, caret: { x: 578.8, y: 452.2 } },

{ label: 'Invested $', x: 735.1, y: 450.6, w: 35 },

{ label: 'Action', x: 902.5, y: 450, w: 23 },

]

const positionRows = [

{

symbol: 'BTC',

symbolW: 23,

name: 'Bitcoin',

nameX: 44.4,

nameW: 20,

change: '+9.10%',

changeW: 38,

y: 469.2,

cells: [469.2, 467.5, 464.8],

cellX: [123.5, 372.2, 549.5],

riskY: 476.8,

invested: '1.3457820',

delay: 1.4,

},

{

symbol: 'ETH',

symbolW: 24,

name: 'Ethereum',

nameX: 45.4,

nameW: 28,

change: '+6.50%',

changeW: 41,

y: 492.2,

cells: [492.2, 490.6, 487.8],

cellX: [120.2, 368.9, 546.2],

riskY: 499.9,

invested: '0.5757932',

delay: 1.5,

},

{

symbol: 'USDT',

symbolW: 32,

name: 'Teher',

nameX: 53.4,

nameW: 17,

change: '+4.11%',

changeW: 35,

y: 515.3,

cells: [515.3, 513.7, 510.9],

cellX: [126.7, 375.3, 552.5],

riskY: 523,

invested: '8.320421',

delay: 1.6,

},

{

symbol: 'BNB',

symbolW: 25,

name: 'BNB',

nameX: 46.3,

nameW: 14,

change: '+8.02%',

changeW: 41,

y: 538.3,

cells: [538.3, 536.7, 534],

cellX: [121.2, 369.8, 547],

riskY: 546,

invested: '2.57572321',

delay: 1.7,

},

]

function OpenPositions() {

return (

<>

{positionTabs.map((tab, i) => (

<Pop

key={tab.label}

x={tab.x}

y={420.5}

w={tab.w}

h={17.4}

delay={1.15 + i * 0.07}

background={tab.active ? '#000' : '#eeeeee'}

>

<T

x={4.4}

y={2.2}

w={tab.textW}

h={13}

size={8.78}

lh={12.9}

color={tab.active ? '#fff' : 'rgba(0,0,0,0.8)'}

>

{tab.label}

</T>

</Pop>

))}

<Pop x={718} y={420.5} w={92} h={17.4} delay={1.2} background="#eeeeee">

<Icon src={calendarIcon} x={4.4} y={4.3} size={8.8} />

<T x={18.7} y={2.2} w={54} h={13} size={8.78} lh={12.9}>

May 1 - May 31

</T>

<Caret x={78.3} y={4.3} w={9.3} h={8.8} color="rgba(0,0,0,0.4)" />

</Pop>

<Pop x={814.4} y={420.5} w={62.9} h={17.4} delay={1.25} background="#eeeeee">

<T x={4.4} y={2.2} w={29} h={13} size={8.78} lh={12.9} color="rgba(0,0,0,0.4)">

Sort By

</T>

<T x={38.3} y={2.2} w={10} h={13} size={8.78} lh={12.9}>

All

</T>

<Caret x={49.2} y={4.3} w={9.3} h={8.8} color="rgba(0,0,0,0.4)" />

</Pop>

<Pop x={881.7} y={420.5} w={48.8} h={17.4} delay={1.3} background="#eeeeee">

<Icon src={importIcon} x={4.4} y={4.3} size={8.8} />

<T x={18.6} y={2.2} w={26} h={13} size={8.78} lh={12.9}>

Export

</T>

</Pop>

{positionColumns.map((column, i) => (

<div key={`${column.label}-${column.x}`}>

<T

x={column.x}

y={column.y}

w={column.w}

h={11}

size={7.69}

lh={11.3}

color="rgba(0,0,0,0.4)"

delay={1.3 + i * 0.04}

>

{column.label}

</T>

{column.caret && <Caret x={column.caret.x} y={column.caret.y} w={9.3} h={8.8} color="rgba(0,0,0,0.4)" />}

</div>

))}

<Line x={17} y={465.3} w={914} h={0.55} delay={1.3} />

{positionRows.map((row) => (

<div key={row.symbol}>

<T x={17} y={row.y} w={row.symbolW} h={18} size={12.08} lh={17.8} weight={700} delay={row.delay}>

{row.symbol}

</T>

<T

x={row.nameX}

y={row.y + 4}

w={row.nameW}

h={10}

size={6.59}

lh={9.7}

color="rgba(0,0,0,0.4)"

delay={row.delay + 0.05}

>

{row.name}

</T>

{row.cellX.map((x, i) => (

<T

key={x}

x={x}

y={row.cells[i]}

w={row.changeW}

h={18}

size={12.08}

lh={17.8}

align="right"

delay={row.delay + 0.05 + i * 0.05}

>

<CountUp value={row.change} delay={row.delay + 0.1 + i * 0.05} duration={0.9} />

</T>

))}

{[0, 1, 2].map((i) => (

<Pop

key={i}

x={260.7 + i * 9.9}

y={row.riskY}

w={8.2}

h={1.6}

delay={row.delay + 0.15 + i * 0.05}

background={i === 0 ? '#121212' : 'rgba(18,18,18,0.2)'}

/>

))}

<T

x={700}

y={row.y}

w={70.4}

h={18}

size={12.08}

lh={17.8}

ls={0}

weight={400}

align="right"

delay={row.delay + 0.2}

>

{row.invested}

</T>

<Pop

x={896.4}

y={row.y + 2.2}

w={32.9}

h={12.1}

delay={row.delay + 0.25}

border="0.55px solid rgba(0,0,0,0.2)"

radius={999}

>

<T x={0} y={0} w={32.9} h={12.1} size={7.69} lh={11.3} align="center">

End

</T>

</Pop>

<Line x={17} y={row.y + 18.7} w={914} h={0.55} delay={row.delay} />

</div>

))}

</>

)

}

/* ---------- card ---------- */

type DashboardProps = {

x: number

y: number

width: number

height: number

scale?: number

radius?: number

zIndex?: number

revealDelay?: number

}

export default function PortfolioDashboard({

x,

y,

width,

height,

scale = 1,

radius = 7.11,

zIndex,

revealDelay = 0,

}: DashboardProps) {

const ref = useRef<HTMLDivElement>(null)

const active = useInView(ref, { once: true, amount: 0.2 })

return (

<motion.div

ref={ref}

className="absolute overflow-hidden"

style={{ left: x, top: y, width, height, borderRadius: radius, background: '#fbfbfb', zIndex }}

initial={{ y: 40, opacity: 0 }}

animate={{ y: 0, opacity: 1 }}

transition={{ duration: 0.7, delay: revealDelay, ease: EASE }}

>

<div

className="absolute left-0 top-0"

style={{

width: CANVAS_WIDTH,

height: CANVAS_HEIGHT,

transform: `scale(${scale})`,

transformOrigin: 'top left',

fontFamily: 'var(--font-display)',

}}

>

<ActiveContext.Provider value={active}>

<NavBar />

<Header />

<Line x={17.57} y={71.91} w={912.87} h={0.55} delay={0.3} />

<PortfolioValue />

<Statistics />

<Line x={17.02} y={221.77} w={912.87} h={0.55} delay={0.65} />

<ValueChart />

<Allocation />

<OpenPositions />

</ActiveContext.Provider>

</div>

</motion.div>

)

}
