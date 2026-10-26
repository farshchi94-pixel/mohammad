
import { useEffect, useRef, useState, type CSSProperties } from 'react'

import { motion, useInView, animate } from 'framer-motion'

const proCardBg = 'https://qclay.design/lovable/kraken/pricing-pro-card-bg.webp'

const arrowBullet = 'https://qclay.design/lovable/kraken/tickers-arrow-right-chunky.svg'

import { popIn, AnimatedLines, DrumText } from '../lib/animations'

import FlowGradient from '../lib/FlowGradient'

const TEXT_STEP = 0.03

const CARD_ITEM_OFFSET = 0.15

function CountUpPrice({

value,

isInView,

delay = 0,

duration = 1,

className,

style,

}: {

value: number

isInView: boolean

delay?: number

duration?: number

className?: string

style?: CSSProperties

}) {

const [display, setDisplay] = useState(0)

const started = useRef(false)

useEffect(() => {

if (!isInView || started.current) return

started.current = true

const controls = animate(0, value, {

duration,

delay,

ease: 'easeOut',

onUpdate: (v) => setDisplay(v),

})

return () => controls.stop()

}, [isInView, value, duration, delay])

return (

<div className={className} style={style}>

${display.toFixed(2).replace('.', ',')}

</div>

)

}

const DESIGN_WIDTH = 1513

const DESIGN_HEIGHT = 1104

const PAD_X = 80

const PAD_Y = 120

const CONTENT_WIDTH = 1353

const CONTENT_HEIGHT = 864

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

const MOBILE_DESIGN_WIDTH = 420

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

function ArrowRight({ color }: { color: string }) {

return (

<svg width="11" height="11" viewBox="0 0 11 11" fill="none">

<path

d="M1 5.5H10M10 5.5L6.5 2M10 5.5L6.5 9"

stroke={color}

strokeWidth="1.3"

strokeLinecap="round"

strokeLinejoin="round"

/>

</svg>

)

}

function PlanBadge({

x,

y,

label,

isInView,

delay = 0,

}: {

x: number

y: number

label: string

isInView: boolean

delay?: number

}) {

return (

<div className="absolute flex items-center gap-[9px]" style={{ left: x, top: y }}>

<motion.span className="h-[10px] w-[10px] shrink-0 bg-white" {...popIn(isInView, delay * 1000)} />

<AnimatedLines

as="span"

lines={[label]}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="whitespace-nowrap text-[16px] text-white/60"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

</div>

)

}

function PriceTag({

x,

y,

value,

isInView,

delay = 0,

}: {

x: number

y: number

value: number

isInView: boolean

delay?: number

}) {

return (

<div className="absolute" style={{ left: x, top: y }}>

<CountUpPrice

value={value}

isInView={isInView}

delay={delay}

className="text-[88px] leading-[88px] text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-2.64px' }}

/>

<AnimatedLines

lines={['/year']}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="text-[80px] leading-[80px] text-white/40"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-2.4px' }}

/>

</div>

)

}

function FeatureRow({

x,

y,

label,

isInView,

delay = 0,

}: {

x: number

y: number

label: string

isInView: boolean

delay?: number

}) {

return (

<div className="absolute flex items-center gap-[7px]" style={{ left: x, top: y }}>

<motion.img src={arrowBullet} alt="" width={14} height={12.6} {...popIn(isInView, delay * 1000)} />

<AnimatedLines

as="span"

lines={[label]}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="whitespace-nowrap text-[16px] text-white/80"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

</div>

)

}

function PlanButton({

x,

y,

width,

label,

isInView,

delay = 0,

}: {

x: number

y: number

width: number

label: string

isInView: boolean

delay?: number

}) {

const [hovering, setHovering] = useState(false)

return (

<motion.div

className="absolute flex h-[30px] items-center justify-center gap-[7px] bg-white px-[9px]"

style={{ left: x, top: y, width }}

{...popIn(isInView, delay * 1000)}

onMouseEnter={() => setHovering(true)}

onMouseLeave={() => setHovering(false)}

>

<DrumText

text={label}

hovering={hovering}

className="whitespace-nowrap text-[14px] font-medium text-black"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.14px' }}

/>

<span className="h-[16px] w-px bg-black/10" />

<ArrowRight color="black" />

</motion.div>

)

}

function MobilePlanBadge({ label, isInView, delay = 0 }: { label: string; isInView: boolean; delay?: number }) {

return (

<div className="flex items-center gap-[9px]">

<motion.span className="h-[10px] w-[10px] shrink-0 bg-white" {...popIn(isInView, delay * 1000)} />

<AnimatedLines

as="span"

lines={[label]}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="whitespace-nowrap text-[16px] text-white/60"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

</div>

)

}

function MobilePriceTag({ value, isInView, delay = 0 }: { value: number; isInView: boolean; delay?: number }) {

return (

<div className="mt-[16px]">

<CountUpPrice

value={value}

isInView={isInView}

delay={delay}

className="text-[56px] leading-[56px] text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-1.68px' }}

/>

<AnimatedLines

lines={['/year']}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="text-[48px] leading-[48px] text-white/40"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-1.44px' }}

/>

</div>

)

}

function MobileFeatureRow({ label, isInView, delay = 0 }: { label: string; isInView: boolean; delay?: number }) {

return (

<div className="flex items-center gap-[7px]">

<motion.img src={arrowBullet} alt="" width={14} height={12.6} {...popIn(isInView, delay * 1000)} />

<AnimatedLines

as="span"

lines={[label]}

baseDelay={delay + TEXT_STEP}

isInView={isInView}

className="whitespace-nowrap text-[15px] text-white/80"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.45px' }}

/>

</div>

)

}

function MobilePlanButton({ label, isInView, delay = 0 }: { label: string; isInView: boolean; delay?: number }) {

const [hovering, setHovering] = useState(false)

return (

<motion.div

className="flex h-[42px] w-full items-center justify-center gap-[7px] bg-white px-[9px]"

{...popIn(isInView, delay * 1000)}

onMouseEnter={() => setHovering(true)}

onMouseLeave={() => setHovering(false)}

>

<DrumText

text={label}

hovering={hovering}

className="whitespace-nowrap text-[14px] font-medium text-black"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.14px' }}

/>

<span className="h-[16px] w-px bg-black/10" />

<ArrowRight color="black" />

</motion.div>

)

}

const traderFeatures = [

'Spot trading access',

'Standard trading fees',

'Basic market analytics',

'Standard support',

]

const proFeatures = [

'Lower trading fees',

'Advanced analytics',

'Real-time trading signals',

'Copy trading tools',

'Advanced risk controls',

]

export default function Pricing() {

const canvas = useFitScale(DESIGN_WIDTH)

const headerRef = useRef<HTMLDivElement>(null)

const headerInView = useInView(headerRef, { once: true, amount: 0.4 })

const cardsRef = useRef<HTMLDivElement>(null)

const cardsInView = useInView(cardsRef, { once: true, amount: 0.2 })

const mobile = useFitScaleAuto(MOBILE_DESIGN_WIDTH)

const mobileHeaderRef = useRef<HTMLDivElement>(null)

const mobileHeaderInView = useInView(mobileHeaderRef, { once: true, amount: 0.4 })

const mobileCardsRef = useRef<HTMLDivElement>(null)

const mobileCardsInView = useInView(mobileCardsRef, { once: true, amount: 0.2 })

const traderBase = 0

const proBase = 0.1

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

<div className="absolute" style={{ left: PAD_X, top: PAD_Y, width: CONTENT_WIDTH, height: CONTENT_HEIGHT }}>

{/* header */}

<motion.div

ref={headerRef}

className="absolute inline-flex items-center gap-[6px] whitespace-nowrap border border-white/10 bg-white/10 px-[10px] py-[6px]"

style={{ left: 0, top: 0 }}

{...popIn(headerInView, 0)}

>

<span

className="h-[6px] w-[6px] shrink-0"

style={{ background: 'linear-gradient(180deg, #FF6215 0%, #FFF28E 100%)' }}

/>

<span

className="text-[13px] font-medium uppercase text-white/80"

style={{ fontFamily: 'var(--font-display)' }}

>

Upgrade

</span>

</motion.div>

<AnimatedLines

as="h2"

lines={['Choose the Plan That', 'Fits Your Trading']}

baseDelay={0.05}

isInView={headerInView}

className="absolute font-medium text-white"

style={{

left: 0,

top: 36,

width: 561,

fontFamily: 'var(--font-display)',

fontSize: 54,

lineHeight: '51.84px',

letterSpacing: '-1.62px',

}}

/>

<div ref={cardsRef} className="absolute" style={{ left: 0, top: 197, width: CONTENT_WIDTH, height: 667 }}>

{/* trader card */}

<motion.div

className="absolute border border-white/20"

style={{

left: 0,

top: 0,

width: 669,

height: 667,

background: 'linear-gradient(160deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 100%)',

}}

initial={{ y: 24, opacity: 0 }}

animate={cardsInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, ease: 'easeOut' }}

>

<PlanBadge x={38} y={31} label="TRADER PLAN" isInView={cardsInView} delay={traderBase + CARD_ITEM_OFFSET} />

<PriceTag x={38} y={96} value={149} isInView={cardsInView} delay={traderBase + CARD_ITEM_OFFSET + 1 * TEXT_STEP} />

<AnimatedLines

as="p"

lines={['Trade with the essentials.', 'Simple tools for getting', 'started.']}

baseDelay={traderBase + CARD_ITEM_OFFSET + 2 * TEXT_STEP}

isInView={cardsInView}

className="absolute text-[20px] text-white/80"

style={{ left: 38, top: 284, width: 259, fontFamily: 'var(--font-display)', letterSpacing: '-0.6px', lineHeight: '24.8px' }}

/>

<AnimatedLines

lines={['What you get:']}

baseDelay={traderBase + CARD_ITEM_OFFSET + 3 * TEXT_STEP}

isInView={cardsInView}

className="absolute text-[20px] font-medium text-white"

style={{ left: 38, top: 379, fontFamily: 'var(--font-display)', letterSpacing: '-0.6px' }}

/>

{traderFeatures.map((f, i) => (

<FeatureRow

key={f}

x={38}

y={416 + i * 26}

label={f}

isInView={cardsInView}

delay={traderBase + CARD_ITEM_OFFSET + (4 + i) * TEXT_STEP}

/>

))}

<PlanButton

x={38}

y={600}

width={134}

label="Choose Trader"

isInView={cardsInView}

delay={traderBase + CARD_ITEM_OFFSET + (4 + traderFeatures.length) * TEXT_STEP}

/>

</motion.div>

{/* pro card */}

<motion.div

className="absolute overflow-hidden border border-white/20"

style={{ left: 684, top: 0, width: 669, height: 667 }}

initial={{ y: 24, opacity: 0 }}

animate={cardsInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, delay: proBase, ease: 'easeOut' }}

>

<img

src={proCardBg}

alt=""

className="absolute -left-[10px] -top-[10px] h-[calc(100%+20px)] w-[calc(100%+20px)] object-cover"

style={{ filter: 'blur(10px)', transform: 'scale(3)', transformOrigin: '50% 85%' }}

/>

{/* live shader gradient over the static fallback image; swirls around the cursor */}

<FlowGradient />

<div className="absolute inset-0 bg-[#E5710A]/10" />

<div

className="absolute inset-0"

style={{ background: 'linear-gradient(160deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)' }}

/>

<PlanBadge x={38} y={31} label="PRO PLAN" isInView={cardsInView} delay={proBase + CARD_ITEM_OFFSET} />

<PriceTag x={38} y={96} value={299} isInView={cardsInView} delay={proBase + CARD_ITEM_OFFSET + 1 * TEXT_STEP} />

<AnimatedLines

as="p"

lines={['More power, deeper insights, and better', 'conditions for active traders.']}

baseDelay={proBase + CARD_ITEM_OFFSET + 2 * TEXT_STEP}

isInView={cardsInView}

className="absolute text-[20px] text-white/80"

style={{ left: 38, top: 284, width: 357, fontFamily: 'var(--font-display)', letterSpacing: '-0.6px', lineHeight: '24.8px' }}

/>

<AnimatedLines

lines={['What you get:']}

baseDelay={proBase + CARD_ITEM_OFFSET + 3 * TEXT_STEP}

isInView={cardsInView}

className="absolute text-[20px] font-medium text-white"

style={{ left: 38, top: 379, fontFamily: 'var(--font-display)', letterSpacing: '-0.6px' }}

/>

{proFeatures.map((f, i) => (

<FeatureRow

key={f}

x={38}

y={416 + i * 26}

label={f}

isInView={cardsInView}

delay={proBase + CARD_ITEM_OFFSET + (4 + i) * TEXT_STEP}

/>

))}

<PlanButton

x={38}

y={600}

width={135}

label="Upgrade to Pro"

isInView={cardsInView}

delay={proBase + CARD_ITEM_OFFSET + (4 + proFeatures.length) * TEXT_STEP}

/>

</motion.div>

</div>

</div>

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

className="absolute left-0 top-0"

style={{ width: MOBILE_DESIGN_WIDTH, transform: `scale(${mobile.scale})`, transformOrigin: 'top left' }}

>

<div className="px-[20px] py-[60px]">

<motion.div

ref={mobileHeaderRef}

className="inline-flex items-center gap-[6px] whitespace-nowrap border border-white/10 bg-white/10 px-[10px] py-[6px]"

{...popIn(mobileHeaderInView, 0)}

>

<span

className="h-[6px] w-[6px] shrink-0"

style={{ background: 'linear-gradient(180deg, #FF6215 0%, #FFF28E 100%)' }}

/>

<span

className="text-[13px] font-medium uppercase text-white/80"

style={{ fontFamily: 'var(--font-display)' }}

>

Upgrade

</span>

</motion.div>

<AnimatedLines

as="h2"

lines={['Choose the Plan That Fits Your Trading']}

baseDelay={0.05}

isInView={mobileHeaderInView}

className="mt-[20px] font-medium text-white"

style={{

fontFamily: 'var(--font-display)',

fontSize: 32,

lineHeight: '36px',

letterSpacing: '-0.96px',

}}

/>

<div ref={mobileCardsRef} className="mt-[32px] flex flex-col gap-[20px]">

{/* trader card */}

<motion.div

className="relative border border-white/20 px-[24px] py-[28px]"

style={{

background: 'linear-gradient(160deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 100%)',

}}

initial={{ y: 24, opacity: 0 }}

animate={mobileCardsInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, ease: 'easeOut' }}

>

<MobilePlanBadge label="TRADER PLAN" isInView={mobileCardsInView} delay={traderBase + CARD_ITEM_OFFSET} />

<MobilePriceTag value={149} isInView={mobileCardsInView} delay={traderBase + CARD_ITEM_OFFSET + 1 * TEXT_STEP} />

<AnimatedLines

as="p"

lines={['Trade with the essentials. Simple tools for getting started.']}

baseDelay={traderBase + CARD_ITEM_OFFSET + 2 * TEXT_STEP}

isInView={mobileCardsInView}

className="mt-[16px] text-[16px] text-white/80"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px', lineHeight: '20.8px' }}

/>

<AnimatedLines

lines={['What you get:']}

baseDelay={traderBase + CARD_ITEM_OFFSET + 3 * TEXT_STEP}

isInView={mobileCardsInView}

className="mt-[20px] text-[16px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

<div className="mt-[12px] flex flex-col gap-[10px]">

{traderFeatures.map((f, i) => (

<MobileFeatureRow

key={f}

label={f}

isInView={mobileCardsInView}

delay={traderBase + CARD_ITEM_OFFSET + (4 + i) * TEXT_STEP}

/>

))}

</div>

<div className="mt-[24px]">

<MobilePlanButton

label="Choose Trader"

isInView={mobileCardsInView}

delay={traderBase + CARD_ITEM_OFFSET + (4 + traderFeatures.length) * TEXT_STEP}

/>

</div>

</motion.div>

{/* pro card */}

<motion.div

className="relative overflow-hidden border border-white/20 px-[24px] py-[28px]"

initial={{ y: 24, opacity: 0 }}

animate={mobileCardsInView ? { y: 0, opacity: 1 } : { y: 24, opacity: 0 }}

transition={{ duration: 0.6, delay: proBase, ease: 'easeOut' }}

>

<img

src={proCardBg}

alt=""

className="absolute -left-[10px] -top-[10px] h-[calc(100%+20px)] w-[calc(100%+20px)] object-cover"

style={{ filter: 'blur(10px)', transform: 'scale(3)', transformOrigin: '50% 85%' }}

/>

{/* live shader gradient over the static fallback image; swirls around the cursor */}

<FlowGradient />

<div className="absolute inset-0 bg-[#E5710A]/10" />

<div

className="absolute inset-0"

style={{ background: 'linear-gradient(160deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)' }}

/>

<div className="relative">

<MobilePlanBadge label="PRO PLAN" isInView={mobileCardsInView} delay={proBase + CARD_ITEM_OFFSET} />

<MobilePriceTag value={299} isInView={mobileCardsInView} delay={proBase + CARD_ITEM_OFFSET + 1 * TEXT_STEP} />

<AnimatedLines

as="p"

lines={['More power, deeper insights, and better conditions for active traders.']}

baseDelay={proBase + CARD_ITEM_OFFSET + 2 * TEXT_STEP}

isInView={mobileCardsInView}

className="mt-[16px] text-[16px] text-white/80"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px', lineHeight: '20.8px' }}

/>

<AnimatedLines

lines={['What you get:']}

baseDelay={proBase + CARD_ITEM_OFFSET + 3 * TEXT_STEP}

isInView={mobileCardsInView}

className="mt-[20px] text-[16px] font-medium text-white"

style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.48px' }}

/>

<div className="mt-[12px] flex flex-col gap-[10px]">

{proFeatures.map((f, i) => (

<MobileFeatureRow

key={f}

label={f}

isInView={mobileCardsInView}

delay={proBase + CARD_ITEM_OFFSET + (4 + i) * TEXT_STEP}

/>

))}

</div>

<div className="mt-[24px]">

<MobilePlanButton

label="Upgrade to Pro"

isInView={mobileCardsInView}

delay={proBase + CARD_ITEM_OFFSET + (4 + proFeatures.length) * TEXT_STEP}

/>

</div>

</div>

</motion.div>

</div>

</div>

</div>

</div>

</section>

</>

)

}
