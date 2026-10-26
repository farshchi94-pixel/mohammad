
import { useEffect, useRef, useState, type CSSProperties } from 'react'

import { motion, useInView, animate } from 'framer-motion'

const octopusTexture = 'https://qclay.design/lovable/kraken/tickers-octopus-texture.webp'

const arrowRightChunky = 'https://qclay.design/lovable/kraken/tickers-arrow-right-chunky.svg'

const arrowLeftChunky = 'https://qclay.design/lovable/kraken/tickers-arrow-left-chunky.svg'

const swapIcon = 'https://qclay.design/lovable/kraken/tickers-swap-icon.svg'

const chevronDown = 'https://qclay.design/lovable/kraken/tickers-chevron-down.svg'

import { popIn, AnimatedLines, DrumText, ScrambleText } from '../lib/animations'

import DotMatrix, { type DotMatrixCrop } from '../lib/DotMatrix'

import TickerCells, { type CellRect } from './TickerCells'

const TEXT_STEP = 0.03

function CountUpNumber({

value,

decimals = 0,

isInView,

delay = 0,

duration = 1,

className,

style,

}: {

value: number

decimals?: number

isInView: boolean

delay?: number

duration?: number

className?: string

style?: CSSProperties

}) {

const [display, setDisplay] = useState(0)

const started = useRef(false)

const prevValue = useRef(value)

useEffect(() => {

if (!isInView) return

if (!started.current) {

started.current = true

prevValue.current = value

const controls = animate(0, value, {

duration,

delay,

ease: 'easeOut',

onUpdate: (v) => setDisplay(v),

})

return () => controls.stop()

}

if (prevValue.current !== value) {

const from = prevValue.current

prevValue.current = value

const controls = animate(from, value, {

duration: 0.4,

ease: 'easeOut',

onUpdate: (v) => setDisplay(v),

})

return () => controls.stop()

}

}, [isInView, value, duration, delay])

return (

<span className={className} style={style}>

{display.toFixed(decimals)}

</span>

)

}

const DESIGN_WIDTH = 1545

const DESIGN_HEIGHT = 922

function useFitScale(designWidth: number) {

const ref = useRef<HTMLDivElement>(null)

const [scale, setScale] = useState(1)

useEffect(() => {

const el = ref.current

if (!el) return

const observer = new ResizeObserver((entries) => {

const width = entries[0]?.contentRect.width

if (width) setScale(width / designWidth)

})

observer.observe(el)

return () => observer.disconnect()

}, [designWidth])

return { ref, scale }

}

function useFitScaleAuto(designWidth: number) {

const outerRef = useRef<HTMLDivElement>(null)

const innerRef = useRef<HTMLDivElement>(null)

const [scale, setScale] = useState(1)

const [naturalHeight, setNaturalHeight] = useState(0)

useEffect(() => {

const el = outerRef.current

if (!el) return

const observer = new ResizeObserver((entries) => {

const width = entries[0]?.contentRect.width

if (width) setScale(width / designWidth)

})

observer.observe(el)

return () => observer.disconnect()

}, [designWidth])

useEffect(() => {

const el = innerRef.current

if (!el) return

const observer = new ResizeObserver((entries) => {

const height = entries[0]?.contentRect.height

if (height) setNaturalHeight(height)

})

observer.observe(el)

return () => observer.disconnect()

}, [])

return { outerRef, innerRef, scale, naturalHeight }

}

const MOBILE_DESIGN_WIDTH = 420

function MobileCoinChip({ label }: { label: string }) {

return (

<span

className="whitespace-nowrap border border-white/10 bg-white/5 px-[9px] py-[6px] text-[12px] font-medium text-white/60"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.36px' }}

>

{label}

</span>

)

}

const vLines = [117, 243, 369, 495, 622, 748, 873, 1000, 1126, 1252, 1378]

const hLines = [0, 114.5, 229, 343.5, 458, 572.5, 687, 801.5, 916]

const coinLabels = [

{ label: 'USDC', x: 218, y: 103 },

{ label: 'BTC', x: 733, y: 103 },

{ label: 'DOGE', x: 1100, y: 103 },

{ label: 'USDC', x: 1495, y: 103 },

{ label: 'ETH', x: 353, y: 217 },

{ label: 'EOS', x: 988, y: 217 },

{ label: 'SOL', x: 1362, y: 217 },

{ label: 'USDC', x: 344, y: 561 },

{ label: 'ETH', x: 102, y: 677 },

{ label: 'XLM', x: 1235, y: 677 },

{ label: 'USDC', x: 723, y: 790 },

{ label: 'BTC', x: 1111, y: 790 },

]

// each tile shows a different part of the 450x562 tentacle texture (crops keep

// the tile's ~1.1 aspect), so the four blocks don't read as the same picture

const textureTiles: { x: number; y: number; crop: DotMatrixCrop; flipX?: boolean }[] = [

{ x: 1127.1, y: 229.8, crop: { x: 190, y: 20, w: 260, h: 236 } },

{ x: 370, y: 1, crop: { x: 20, y: 250, w: 230, h: 208 }, flipX: true },

{ x: 244, y: 688, crop: { x: 0, y: 360, w: 225, h: 204 } },

{ x: 1379, y: 802.5, crop: { x: 225, y: 300, w: 225, h: 204 } },

]

const TEXTURE_TILE_WIDTH = 125.38

const TEXTURE_TILE_HEIGHT = 113.6

// empty grid cells that react to the cursor: edges of the drawn grid, minus

// the swap widget and the texture tiles

const CELL_COL_EDGES = [0, ...vLines, DESIGN_WIDTH]

const CELL_BLOCKED: CellRect[] = [

{ x: 513, y: 258, w: 486, h: 385 },

...textureTiles.map((t) => ({ x: t.x, y: t.y, w: TEXTURE_TILE_WIDTH, h: TEXTURE_TILE_HEIGHT })),

]

const BLIND_ROWS = 4

const BLIND_COLOR = '#08090b'

function ImageBlinds({

left,

top,

width,

height,

isInView,

baseDelay = 0,

leftExtraBleed = 0,

rightExtraBleed = 0,

bottomExtraBleed = 0,

}: {

left: number

top: number

width: number

height: number

isInView: boolean

baseDelay?: number

leftExtraBleed?: number

rightExtraBleed?: number

bottomExtraBleed?: number

}) {

const rowHeight = height / BLIND_ROWS

return (

<>

{Array.from({ length: BLIND_ROWS }).map((_, i) => {

const isFirst = i === 0

const isLast = i === BLIND_ROWS - 1

// Outer top/bottom edges are trimmed 1px inward (no bleed past the image).

// Internal seams between rows keep a 1px bleed each way so rounding

// never leaves a hairline gap between adjacent rows.

const rowTop = top + i * rowHeight + (isFirst ? 1 : -1)

const rowBottom = top + (i + 1) * rowHeight + (isLast ? -1 + bottomExtraBleed : 1)

const rowLeft = left + 1 - leftExtraBleed

const rowRight = left + width - 1 + rightExtraBleed

return (

<motion.div

key={i}

className="absolute"

style={{

left: rowLeft,

top: rowTop,

width: rowRight - rowLeft,

height: rowBottom - rowTop,

backgroundColor: BLIND_COLOR,

transformOrigin: 'bottom',

}}

initial={{ scaleY: 1 }}

animate={isInView ? { scaleY: 0 } : undefined}

transition={{ duration: 0.5, delay: baseDelay + i * 0.12, ease: 'easeOut' }}

/>

)

})}

</>

)

}

const sparkleDotsLeft = [

{ x: 508, y: 578, s: 2 },

{ x: 523, y: 615, s: 1 },

{ x: 548, y: 596, s: 1 },

{ x: 562, y: 582, s: 1 },

{ x: 562, y: 621, s: 1 },

{ x: 580, y: 601, s: 1 },

{ x: 601, y: 610, s: 1 },

{ x: 621, y: 599, s: 1 },

{ x: 605, y: 583, s: 1 },

{ x: 621, y: 628, s: 1 },

{ x: 647, y: 577, s: 1 },

]

const sparkleDotsRight = sparkleDotsLeft.map((d) => ({ ...d, x: d.x + 154 }))

function CoinLabel({

label,

x,

y,

isInView,

delay = 0,

}: {

label: string

x: number

y: number

isInView: boolean

delay?: number

}) {

return (

<motion.div

className="absolute whitespace-nowrap bg-[#08090b] px-[9px] py-[6px] text-[12px] font-medium text-white/60"

style={{ left: x, top: y, fontFamily: 'var(--font-display)', letterSpacing: '-0.36px' }}

{...popIn(isInView, delay)}

>

{label}

</motion.div>

)

}

const mobileChipLabels = ['USDC', 'BTC', 'DOGE', 'ETH', 'SOL', 'XLM']

const SWAP_COINS = ['USDC', 'ETH', 'BTC', 'SOL']

const SWAP_ICON_HOVER = 'transition-transform duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] group-hover:rotate-180 group-active:scale-90'

const CODE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

const COIN_HOLD_MS = 2600

const CODE_HOLD_MS = 1400

function randomCode(length: number) {

let out = ''

for (let i = 0; i < length; i++) out += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)]

return out

}

/**

* Loops a coin label between two resting states: the ticker (USDC) and a

* random "encrypted" code of the same length (FJDS) - feed the result to

* ScrambleText so every switch re-rolls the letters: USDC -> FJDS -> USDC -> ...

* Picking another coin restarts the loop from the new ticker.

*/

function useCoinCodeCycle(coin: string) {

const [code, setCode] = useState<string | null>(null)

useEffect(() => {

setCode(null)

let timer = 0

const showCoin = () => {

setCode(null)

timer = window.setTimeout(showCode, COIN_HOLD_MS)

}

const showCode = () => {

setCode(randomCode(coin.length))

timer = window.setTimeout(showCoin, CODE_HOLD_MS)

}

timer = window.setTimeout(showCode, COIN_HOLD_MS)

return () => window.clearTimeout(timer)

}, [coin])

return code ?? coin

}

/** Big coin name beside the swap widget, cycling via useCoinCodeCycle. */

function SideCoinLabel({ coin }: { coin: string }) {

const [hovering, setHovering] = useState(false)

const text = useCoinCodeCycle(coin)

return (

<span

className="text-[64px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-1.92px' }}

onMouseEnter={() => setHovering(true)}

onMouseLeave={() => setHovering(false)}

>

<ScrambleText text={text} trigger={hovering} duration={600} />

</span>

)

}

const COIN_MOCK: Record<string, { amount: number; decimals: number; usd: string }> = {

USDC: { amount: 210.5, decimals: 1, usd: '$210.50' },

ETH: { amount: 0.6842, decimals: 4, usd: '$2.481.30' },

BTC: { amount: 0.0219, decimals: 4, usd: '$1.986.45' },

SOL: { amount: 1904.61, decimals: 2, usd: '$1.905.19' },

}

function useSwapWidget() {

const [sellCoin, setSellCoin] = useState('USDC')

const [buyCoin, setBuyCoin] = useState('SOL')

const [sellMenuOpen, setSellMenuOpen] = useState(false)

const [buyMenuOpen, setBuyMenuOpen] = useState(false)

const sellWrapRef = useRef<HTMLDivElement>(null)

const buyWrapRef = useRef<HTMLDivElement>(null)

useEffect(() => {

if (!sellMenuOpen && !buyMenuOpen) return

function onPointerDown(e: MouseEvent) {

const target = e.target as Node

if (sellWrapRef.current?.contains(target)) return

if (buyWrapRef.current?.contains(target)) return

setSellMenuOpen(false)

setBuyMenuOpen(false)

}

document.addEventListener('mousedown', onPointerDown)

return () => document.removeEventListener('mousedown', onPointerDown)

}, [sellMenuOpen, buyMenuOpen])

function swap() {

setSellCoin(buyCoin)

setBuyCoin(sellCoin)

}

function pickSellCoin(coin: string) {

if (coin === buyCoin) swap()

else setSellCoin(coin)

setSellMenuOpen(false)

}

function pickBuyCoin(coin: string) {

if (coin === sellCoin) swap()

else setBuyCoin(coin)

setBuyMenuOpen(false)

}

return {

sellCoin,

buyCoin,

sellMock: COIN_MOCK[sellCoin],

buyMock: COIN_MOCK[buyCoin],

sellMenuOpen,

buyMenuOpen,

sellWrapRef,

buyWrapRef,

swap,

pickSellCoin,

pickBuyCoin,

toggleSellMenu: () => {

setBuyMenuOpen(false)

setSellMenuOpen((v) => !v)

},

toggleBuyMenu: () => {

setSellMenuOpen(false)

setBuyMenuOpen((v) => !v)

},

}

}

function CoinMenu({

options,

onPick,

width,

}: {

options: string[]

onPick: (coin: string) => void

width: number

}) {

return (

<div

className="absolute left-0 top-[calc(100%+8px)] z-30 border border-white/10 bg-[#151517]"

style={{ width }}

>

{options.map((coin) => (

<button

key={coin}

type="button"

onClick={() => onPick(coin)}

className="block w-full px-[9px] py-[8px] text-left text-[16px] font-normal text-white hover:bg-white/10"

style={{ fontFamily: 'var(--font-display)' }}

>

{coin}

</button>

))}

</div>

)

}

export default function TickerGrid() {

const canvas = useFitScale(DESIGN_WIDTH)

const mobile = useFitScaleAuto(MOBILE_DESIGN_WIDTH)

const textureRef = useRef<HTMLDivElement>(null)

const textureInView = useInView(textureRef, { once: true, amount: 0.2 })

const swapRef = useRef<HTMLDivElement>(null)

const swapInView = useInView(swapRef, { once: true, amount: 0.2 })

const labelsInView = useInView(canvas.ref, { once: true, amount: 0.1 })

const mobileSwapRef = useRef<HTMLDivElement>(null)

const mobileSwapInView = useInView(mobileSwapRef, { once: true, amount: 0.2 })

const [connectHovering, setConnectHovering] = useState(false)

const [mobileConnectHovering, setMobileConnectHovering] = useState(false)

const desktopSwap = useSwapWidget()

const mobileSwap = useSwapWidget()

const mobileSellLabel = useCoinCodeCycle(mobileSwap.sellCoin)

const mobileBuyLabel = useCoinCodeCycle(mobileSwap.buyCoin)

return (

<>

<section

ref={canvas.ref}

className="relative hidden w-full overflow-hidden bg-[#08090b] lg:block"

style={{ aspectRatio: `${DESIGN_WIDTH} / ${DESIGN_HEIGHT}` }}

>

<div

className="absolute left-0 top-0"

style={{

width: DESIGN_WIDTH,

height: DESIGN_HEIGHT,

transform: `scale(${canvas.scale})`,

transformOrigin: 'top left',

}}

>

{/* hover trail + unfolding quote cards in the empty cells */}

<TickerCells

colEdges={CELL_COL_EDGES}

rowEdges={hLines}

width={DESIGN_WIDTH}

height={DESIGN_HEIGHT}

blocked={CELL_BLOCKED}

/>

{/* grid lines: drawn in from their center, expanding both ways */}

{vLines.map((x, i) => (

<motion.span

key={x}

className="absolute top-0 w-px bg-white/20"

style={{ left: x, height: DESIGN_HEIGHT }}

initial={{ scaleY: 0 }}

animate={labelsInView ? { scaleY: 1 } : { scaleY: 0 }}

transition={{ duration: 0.6, ease: 'easeOut', delay: i * 0.04 }}

/>

))}

{hLines.map((y, i) => (

<motion.span

key={y}

className={`absolute left-0 h-px ${i === 0 || i === hLines.length - 1 ? 'bg-white/25' : 'bg-white/20'}`}

style={{ top: y, width: DESIGN_WIDTH }}

initial={{ scaleX: 0 }}

animate={labelsInView ? { scaleX: 1 } : { scaleX: 0 }}

transition={{ duration: 0.6, ease: 'easeOut', delay: vLines.length * 0.04 + i * 0.04 }}

/>

))}

{/* dedicated, real-sized element used purely for visibility detection */}

<div

ref={textureRef}

className="absolute"

style={{ left: textureTiles[0].x, top: textureTiles[0].y, width: TEXTURE_TILE_WIDTH, height: TEXTURE_TILE_HEIGHT }}

/>

{/* decorative texture tiles */}

{textureTiles.map((t, i) => (

<div key={i}>

<DotMatrix

src={octopusTexture}

width={TEXTURE_TILE_WIDTH}

height={TEXTURE_TILE_HEIGHT}

crop={t.crop}

flipX={t.flipX}

pitch={3.4}

gain={1.3}

dotScale={1}

radius={45}

className="absolute opacity-90"

style={{ left: t.x, top: t.y }}

/>

<ImageBlinds

left={t.x}

top={t.y}

width={TEXTURE_TILE_WIDTH}

height={TEXTURE_TILE_HEIGHT}

isInView={textureInView}

baseDelay={i * 0.08}

leftExtraBleed={i === 0 ? 1.75 : i === 1 ? 1 : i === 2 ? 1 : i === 3 ? 2 : 0}

rightExtraBleed={i === 0 ? 1 : i === 1 ? 1 : i === 2 ? 0.5 : i === 3 ? 1 : 0}

bottomExtraBleed={i === 0 ? 1 : i === 1 ? 1 : i === 2 ? 1 : i === 3 ? 2.75 : 0}

/>

</div>

))}

{/* coin labels */}

{coinLabels.map((c, i) => (

<CoinLabel key={i} label={c.label} x={c.x} y={c.y} isInView={labelsInView} delay={i * 30} />

))}

<motion.div

className="absolute text-[12px] font-medium text-white/60"

style={{ left: 350, top: 910, fontFamily: 'var(--font-display)', letterSpacing: '-0.36px' }}

{...popIn(labelsInView, coinLabels.length * 30)}

>

MATIC

</motion.div>

{/* dedicated, real-sized element used purely for visibility detection */}

<div ref={swapRef} className="absolute" style={{ left: 513, top: 258, width: 486, height: 385 }} />

{/* left side: arrow + USDC (slides in left-to-right, fading in) */}

<motion.div

className="absolute flex items-center gap-[15px]"

style={{ left: 69, top: 436 }}

initial={{ x: -60, opacity: 0 }}

animate={swapInView ? { x: 0, opacity: 1 } : { x: -60, opacity: 0 }}

transition={{ duration: 0.7, ease: 'easeOut' }}

>

<motion.img

src={arrowRightChunky}

alt=""

width={53}

height={48}

animate={{ x: [0, 12, 0] }}

transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}

/>

<SideCoinLabel coin={desktopSwap.sellCoin} />

</motion.div>

{/* right side: SOL + arrow (slides in right-to-left, fading in) */}

<motion.div

className="absolute flex items-center gap-[15px]"

style={{ right: DESIGN_WIDTH - 1450, top: 428 }}

initial={{ x: 60, opacity: 0 }}

animate={swapInView ? { x: 0, opacity: 1 } : { x: 60, opacity: 0 }}

transition={{ duration: 0.7, ease: 'easeOut' }}

>

<SideCoinLabel coin={desktopSwap.buyCoin} />

<motion.img

src={arrowLeftChunky}

alt=""

width={53}

height={48}

animate={{ x: [0, -12, 0] }}

transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}

/>

</motion.div>

{/* swap card */}

<AnimatedLines

lines={['Swap']}

baseDelay={0}

isInView={swapInView}

className="absolute text-[24px] font-medium text-white"

style={{ left: 513, top: 258, fontFamily: 'var(--font-display)', letterSpacing: '-0.72px' }}

/>

{/* sell panel */}

<motion.div

className="absolute border border-white/10 backdrop-blur-[10px]"

style={{ left: 513, top: 303, width: 486, height: 128, background: 'rgba(255,255,255,0.07)' }}

initial={{ y: 24, opacity: 0 }}

animate={swapInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, ease: 'easeOut' }}

>

<AnimatedLines

lines={['Sell']}

baseDelay={2 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-white/50"

style={{ left: 20, top: 17, fontFamily: 'var(--font-display)' }}

/>

<CountUpNumber

value={desktopSwap.sellMock.amount}

decimals={desktopSwap.sellMock.decimals}

isInView={swapInView}

delay={3 * TEXT_STEP}

duration={1}

className="absolute text-[40px] font-normal text-white"

style={{ left: 20, top: 43, fontFamily: 'var(--font-display)', letterSpacing: '-1.2px' }}

/>

<AnimatedLines

lines={[desktopSwap.sellMock.usd]}

baseDelay={4 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-white/50"

style={{ left: 20, top: 94, fontFamily: 'var(--font-display)' }}

/>

<AnimatedLines

lines={[`0 ${desktopSwap.sellCoin}`]}

baseDelay={5 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-white/50"

style={{ left: 422, top: 94, fontFamily: 'var(--font-display)' }}

/>

<motion.div

ref={desktopSwap.sellWrapRef}

className="absolute flex items-center gap-[8px] bg-white/10 px-[9px] cursor-pointer select-none"

style={{ left: 365.8, top: 45, width: 100, height: 35 }}

onClick={desktopSwap.toggleSellMenu}

{...popIn(swapInView, 60)}

>

<span

className="text-[24px] font-normal text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.72px' }}

>

{desktopSwap.sellCoin}

</span>

<img src={chevronDown} alt="" width={14} height={14} />

{desktopSwap.sellMenuOpen && (

<CoinMenu

width={100}

options={SWAP_COINS.filter((c) => c !== desktopSwap.sellCoin)}

onPick={desktopSwap.pickSellCoin}

/>

)}

</motion.div>

</motion.div>

{/* swap icon button */}

<motion.div

className="group absolute z-[2] flex items-center justify-center border-[4px] border-[#08090b] bg-[#222325] cursor-pointer transition-colors duration-300 hover:bg-[#FF6215]"

style={{ left: 726, top: 404, width: 60, height: 60 }}

onClick={desktopSwap.swap}

{...popIn(swapInView, 90)}

>

<img src={swapIcon} alt="" width={24} height={24} className={SWAP_ICON_HOVER} />

</motion.div>

{/* buy panel */}

<motion.div

className="absolute bg-white"

style={{ left: 513, top: 435, width: 486, height: 128 }}

initial={{ y: 24, opacity: 0 }}

animate={swapInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, delay: 0.08, ease: 'easeOut' }}

>

<AnimatedLines

lines={['Buy']}

baseDelay={7 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-black"

style={{ left: 20, top: 17, fontFamily: 'var(--font-display)' }}

/>

<CountUpNumber

value={desktopSwap.buyMock.amount}

decimals={desktopSwap.buyMock.decimals}

isInView={swapInView}

delay={8 * TEXT_STEP}

duration={1}

className="absolute text-[40px] font-normal text-black"

style={{ left: 20, top: 45, fontFamily: 'var(--font-display)', letterSpacing: '-1.2px' }}

/>

<AnimatedLines

lines={[desktopSwap.buyMock.usd]}

baseDelay={9 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-black"

style={{ left: 20, top: 94, fontFamily: 'var(--font-display)' }}

/>

<AnimatedLines

lines={[`0 ${desktopSwap.buyCoin}`]}

baseDelay={10 * TEXT_STEP}

isInView={swapInView}

className="absolute text-[16px] font-normal text-black"

style={{ left: 422, top: 94, fontFamily: 'var(--font-display)' }}

/>

<motion.div

ref={desktopSwap.buyWrapRef}

className="absolute flex items-center gap-[8px] rounded-none border border-white/15 bg-black px-[9px] cursor-pointer select-none"

style={{ left: 364, top: 45, width: 102, height: 36.8 }}

onClick={desktopSwap.toggleBuyMenu}

{...popIn(swapInView, 120)}

>

<span

className="text-[24px] font-normal text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.72px' }}

>

{desktopSwap.buyCoin}

</span>

<img src={chevronDown} alt="" width={14} height={14} className="opacity-50" />

{desktopSwap.buyMenuOpen && (

<CoinMenu

width={102}

options={SWAP_COINS.filter((c) => c !== desktopSwap.buyCoin)}

onPick={desktopSwap.pickBuyCoin}

/>

)}

</motion.div>

</motion.div>

{/* connect wallet button */}

<motion.div

className="absolute flex items-center justify-center overflow-hidden bg-[#FF6215]"

style={{ left: 513, top: 583, width: 486, height: 60 }}

initial={{ y: 24, opacity: 0 }}

animate={swapInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, delay: 0.16, ease: 'easeOut' }}

onMouseEnter={() => setConnectHovering(true)}

onMouseLeave={() => setConnectHovering(false)}

>

{sparkleDotsLeft.concat(sparkleDotsRight).map((d, i) => (

<span

key={i}

className="absolute rounded-full bg-white/70"

style={{ left: d.x - 513, top: d.y - 583, width: d.s, height: d.s }}

/>

))}

<span

className="absolute rounded-full"

style={{

left: 213,

top: 5,

width: 60,

height: 30,

background: 'rgba(206,187,150,0.32)',

filter: 'blur(20px)',

}}

/>

<motion.span

className="relative inline-block"

initial={{ y: 10, opacity: 0 }}

animate={swapInView ? { y: 0, opacity: 1 } : { y: 10, opacity: 0 }}

transition={{ duration: 0.5, delay: 0.16 + 13 * TEXT_STEP, ease: 'easeOut' }}

>

<DrumText

text="Connect Wallet"

hovering={connectHovering}

className="text-[20px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.6px' }}

/>

</motion.span>

</motion.div>

</div>

</section>

<section className="relative block w-full overflow-hidden bg-[#08090b] lg:hidden">

<div

ref={mobile.outerRef}

className="relative w-full overflow-hidden"

style={{ height: mobile.naturalHeight * mobile.scale }}

>

<div

ref={mobile.innerRef}

className="absolute left-0 top-0 flex flex-col items-center px-[24px] py-[56px]"

style={{

width: MOBILE_DESIGN_WIDTH,

transform: `scale(${mobile.scale})`,

transformOrigin: 'top left',

}}

>

<div className="mb-[28px] flex flex-wrap items-center justify-center gap-[8px]">

{mobileChipLabels.map((label) => (

<MobileCoinChip key={label} label={label} />

))}

</div>

<div className="mb-[28px] flex items-center gap-[8px]">

<img src={arrowRightChunky} alt="" width={26} height={24} />

<span

className="text-[26px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.78px' }}

>

<ScrambleText text={mobileSellLabel} />

</span>

<span className="text-[26px] font-medium text-white/40">/</span>

<span

className="text-[26px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.78px' }}

>

<ScrambleText text={mobileBuyLabel} />

</span>

<img src={arrowLeftChunky} alt="" width={26} height={24} />

</div>

<div ref={mobileSwapRef} className="flex w-full flex-col items-center">

<AnimatedLines

lines={['Swap']}

isInView={mobileSwapInView}

className="mb-[12px] w-full text-[20px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.6px' }}

/>

<motion.div

className="w-full border border-white/10 backdrop-blur-[10px]"

style={{ background: 'rgba(255,255,255,0.07)', padding: 16 }}

initial={{ y: 16, opacity: 0 }}

animate={mobileSwapInView ? { y: 0, opacity: 1 } : { y: 16, opacity: 0 }}

transition={{ duration: 0.6, ease: 'easeOut' }}

>

<div className="flex items-center justify-between">

<AnimatedLines

lines={['Sell']}

baseDelay={2 * TEXT_STEP}

isInView={mobileSwapInView}

className="text-[14px] font-normal text-white/50"

style={{ fontFamily: 'var(--font-display)' }}

/>

<motion.div

ref={mobileSwap.sellWrapRef}

className="relative flex items-center gap-[6px] bg-white/10 px-[9px] py-[6px] cursor-pointer select-none"

onClick={mobileSwap.toggleSellMenu}

{...popIn(mobileSwapInView, 60)}

>

<span

className="text-[18px] font-normal text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.54px' }}

>

{mobileSwap.sellCoin}

</span>

<img src={chevronDown} alt="" width={12} height={12} />

{mobileSwap.sellMenuOpen && (

<CoinMenu

width={90}

options={SWAP_COINS.filter((c) => c !== mobileSwap.sellCoin)}

onPick={mobileSwap.pickSellCoin}

/>

)}

</motion.div>

</div>

<CountUpNumber

value={mobileSwap.sellMock.amount}

decimals={mobileSwap.sellMock.decimals}

isInView={mobileSwapInView}

delay={3 * TEXT_STEP}

duration={1}

className="mt-[8px] block text-[32px] font-normal text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.96px' }}

/>

<div

className="mt-[8px] flex items-center justify-between text-[13px] font-normal text-white/50"

style={{ fontFamily: 'var(--font-display)' }}

>

<span>{mobileSwap.sellMock.usd}</span>

<span>0 {mobileSwap.sellCoin}</span>

</div>

</motion.div>

<motion.div

className="group relative z-[2] -my-[16px] flex items-center justify-center border-[4px] border-[#08090b] bg-[#222325] cursor-pointer transition-colors duration-300 hover:bg-[#FF6215]"

style={{ width: 48, height: 48 }}

onClick={mobileSwap.swap}

{...popIn(mobileSwapInView, 90)}

>

<img src={swapIcon} alt="" width={20} height={20} className={SWAP_ICON_HOVER} />

</motion.div>

<motion.div

className="w-full bg-white"

style={{ padding: 16 }}

initial={{ y: 16, opacity: 0 }}

animate={mobileSwapInView ? { y: 0, opacity: 1 } : { y: 16, opacity: 0 }}

transition={{ duration: 0.6, delay: 0.08, ease: 'easeOut' }}

>

<div className="flex items-center justify-between">

<AnimatedLines

lines={['Buy']}

baseDelay={7 * TEXT_STEP}

isInView={mobileSwapInView}

className="text-[14px] font-normal text-black"

style={{ fontFamily: 'var(--font-display)' }}

/>

<motion.div

ref={mobileSwap.buyWrapRef}

className="relative flex items-center gap-[6px] border border-white/15 bg-black px-[9px] py-[6px] cursor-pointer select-none"

onClick={mobileSwap.toggleBuyMenu}

{...popIn(mobileSwapInView, 120)}

>

<span

className="text-[18px] font-normal text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.54px' }}

>

{mobileSwap.buyCoin}

</span>

<img src={chevronDown} alt="" width={12} height={12} className="opacity-50" />

{mobileSwap.buyMenuOpen && (

<CoinMenu

width={90}

options={SWAP_COINS.filter((c) => c !== mobileSwap.buyCoin)}

onPick={mobileSwap.pickBuyCoin}

/>

)}

</motion.div>

</div>

<CountUpNumber

value={mobileSwap.buyMock.amount}

decimals={mobileSwap.buyMock.decimals}

isInView={mobileSwapInView}

delay={8 * TEXT_STEP}

duration={1}

className="mt-[8px] block text-[32px] font-normal text-black"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.96px' }}

/>

<div

className="mt-[8px] flex items-center justify-between text-[13px] font-normal text-black"

style={{ fontFamily: 'var(--font-display)' }}

>

<span>{mobileSwap.buyMock.usd}</span>

<span>0 {mobileSwap.buyCoin}</span>

</div>

</motion.div>

<motion.div

className="mt-[16px] flex w-full items-center justify-center overflow-hidden bg-[#FF6215]"

style={{ height: 52 }}

initial={{ y: 16, opacity: 0 }}

animate={mobileSwapInView ? { y: 0, opacity: 1 } : { y: 16, opacity: 0 }}

transition={{ duration: 0.6, delay: 0.16, ease: 'easeOut' }}

onMouseEnter={() => setMobileConnectHovering(true)}

onMouseLeave={() => setMobileConnectHovering(false)}

>

<motion.span

className="relative inline-block"

initial={{ y: 10, opacity: 0 }}

animate={mobileSwapInView ? { y: 0, opacity: 1 } : { y: 10, opacity: 0 }}

transition={{ duration: 0.5, delay: 0.16 + 13 * TEXT_STEP, ease: 'easeOut' }}

>

<DrumText

text="Connect Wallet"

hovering={mobileConnectHovering}

className="text-[16px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

</motion.span>

</motion.div>

</div>

</div>

</div>

</section>

</>

)

}
