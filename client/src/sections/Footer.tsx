
import { useEffect, useRef, useState } from 'react'

import { motion, useInView } from 'framer-motion'

const krakenMark = 'https://qclay.design/lovable/kraken/hero-kraken-mark.svg'

const xIcon = 'https://qclay.design/lovable/kraken/footer-x.svg'

const linkedinIcon = 'https://qclay.design/lovable/kraken/footer-linkedin.svg'

const githubIcon = 'https://qclay.design/lovable/kraken/footer-github.svg'

import { popIn, AnimatedLines, HoverLine } from '../lib/animations'

const DESIGN_WIDTH = 1514

const DESIGN_HEIGHT = 618

const PAD_X = 40

const CONTENT_WIDTH = 1434

const FOOTER_TOP_TRIM_VH = 10

const TEXT_STEP = 0.03

const ITEMS_PER_COLUMN = 7

const MOBILE_DESIGN_WIDTH = 420

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

function scrollToTop() {

window.scrollTo({ top: 0, behavior: 'smooth' })

}

function ArrowUp() {

return (

<svg width="12" height="12" viewBox="0 0 12 12" fill="none">

<path d="M3 4.5L6 1.5L9 4.5" stroke="white" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />

<path d="M6 1.5V10" stroke="white" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />

</svg>

)

}

const columns = [

{

header: 'PRODUCTS',

x: 470,

links: ['Spot Trading', 'Futures', 'Copy Trading', 'Staking', 'Earn', 'Trading Bots'],

},

{

header: 'MARKETS',

x: 705,

links: ['Markets', 'Cryptocurrencies', 'New Listings', 'Top Gainers', 'Market Trends', 'Trading Fees'],

},

{

header: 'TRADERS',

x: 1019,

links: ['Top Traders', 'Copy Trading', 'Leaderboard', 'Become a Trader', 'Referral Program', 'Rewards'],

},

{

header: 'RESOURCES',

x: 1254,

links: ['Learn', 'Trading Guides', 'Market Insights', 'Help Center', 'About Us', 'Contact Us'],

},

]

const legalLinks = ['Legal', 'Privacy', 'Data Privacy', 'Certifications', 'Cookies']

const blurbLines = [

'Trade smarter. Move with the market.',

'A powerful crypto trading platform built to',

'help you track markets, manage positions,',

'and act on opportunities with confidence.',

]

const DASH_BG = 'repeating-linear-gradient(to bottom, rgba(255,255,255,0.1) 0 10px, transparent 10px 18px)'

const DASH_BG_H = 'repeating-linear-gradient(to right, rgba(255,255,255,0.1) 0 10px, transparent 10px 18px)'

const verticalDividers = [

{ left: 0, top: 0, height: 618 },

{ left: CONTENT_WIDTH, top: 0, height: 618 },

{ left: 402, top: 75, height: 500 },

{ left: 439, top: 78, height: 500 },

{ left: 928, top: 75, height: 441 },

{ left: 965, top: 78, height: 441 },

]

const horizontalDividers = [

{ left: 9, top: 519, width: 1424 },

{ left: 0, top: 578, width: 1424 },

]

function DrawInDividers({ isInView }: { isInView: boolean }) {

return (

<>

{verticalDividers.map((d, i) => (

<motion.span

key={`v-${i}`}

className="absolute w-px"

style={{ left: d.left, top: d.top, backgroundImage: DASH_BG }}

initial={{ height: 0 }}

animate={isInView ? { height: d.height } : { height: 0 }}

transition={{ duration: 0.9, ease: 'easeOut', delay: i * 0.08 }}

/>

))}

{horizontalDividers.map((d, i) => (

<motion.span

key={`h-${i}`}

className="absolute h-px"

style={{ left: d.left, top: d.top, backgroundImage: DASH_BG_H }}

initial={{ width: 0 }}

animate={isInView ? { width: d.width } : { width: 0 }}

transition={{ duration: 0.9, ease: 'easeOut', delay: 0.4 + i * 0.08 }}

/>

))}

</>

)

}

function FooterColumn({

header,

x,

links,

colIndex,

isInView,

}: {

header: string

x: number

links: string[]

colIndex: number

isInView: boolean

}) {

const base = 5 + colIndex * ITEMS_PER_COLUMN

return (

<div className="absolute" style={{ left: x, top: 193 }}>

<AnimatedLines

lines={[header]}

baseDelay={base * TEXT_STEP}

isInView={isInView}

className="text-[12px] uppercase text-white/50"

style={{ fontFamily: 'var(--font-mono-label)', letterSpacing: '0.48px' }}

/>

{links.map((link, i) => (

<HoverLine

key={link}

text={link}

baseDelay={(base + 1 + i) * TEXT_STEP}

effect="scramble"

isInView={isInView}

className="absolute whitespace-nowrap text-[16px] font-medium text-white"

style={{ top: 42 + i * 33, fontFamily: 'var(--font-logo)' }}

/>

))}

</div>

)

}

function MobileFooter() {

const mobile = useFitScaleAuto(MOBILE_DESIGN_WIDTH)

const contentRef = useRef<HTMLDivElement>(null)

const inView = useInView(contentRef, { once: true, amount: 0.2 })

const bottomBase = 5 + columns.length * ITEMS_PER_COLUMN

const dashedH = 'repeating-linear-gradient(to right, rgba(255,255,255,0.1) 0 6px, transparent 6px 11px)'

return (

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

<div ref={contentRef} className="flex flex-col gap-[36px] px-[24px] py-[56px]">

{/* logo + blurb */}

<div className="flex flex-col gap-[20px]">

<div className="flex items-center">

<motion.img src={krakenMark} alt="" width={30} height={23} {...popIn(inView, 0)} />

<AnimatedLines

lines={['Kraken']}

baseDelay={0}

isInView={inView}

className="ml-[9px] text-[26px] font-medium text-white"

style={{ fontFamily: 'var(--font-logo)', letterSpacing: '-0.52px' }}

/>

</div>

<AnimatedLines

as="p"

lines={blurbLines.join(' ').split(/(?<=\.)\s+/)}

baseDelay={1 * TEXT_STEP}

isInView={inView}

className="text-[15px] text-white/60"

style={{ fontFamily: 'var(--font-logo)', letterSpacing: '-0.16px', lineHeight: '140%' }}

/>

</div>

{/* social icons */}

<div className="flex items-center gap-[8px]">

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 40)}

>

<img src={xIcon} alt="X" width={18} height={18} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 70)}

>

<img src={linkedinIcon} alt="LinkedIn" width={16} height={16} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 100)}

>

<img src={githubIcon} alt="GitHub" width={16} height={16} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

</div>

<span className="h-px w-full" style={{ backgroundImage: dashedH }} />

{/* link columns */}

<div className="grid grid-cols-2 gap-x-[16px] gap-y-[32px]">

{columns.map((col, i) => {

const base = 5 + i * ITEMS_PER_COLUMN

return (

<div key={col.header} className="flex flex-col">

<AnimatedLines

lines={[col.header]}

baseDelay={base * TEXT_STEP}

isInView={inView}

className="text-[11px] uppercase text-white/50"

style={{ fontFamily: 'var(--font-mono-label)', letterSpacing: '0.44px' }}

/>

<div className="mt-[14px] flex flex-col gap-[12px]">

{col.links.map((link, j) => (

<HoverLine

key={link}

text={link}

baseDelay={(base + 1 + j) * TEXT_STEP}

effect="scramble"

isInView={inView}

className="text-[14px] font-medium text-white"

style={{ fontFamily: 'var(--font-logo)' }}

/>

))}

</div>

</div>

)

})}

</div>

<span className="h-px w-full" style={{ backgroundImage: dashedH }} />

{/* bottom bar */}

<div className="flex flex-col gap-[20px]">

<div className="flex flex-wrap items-center gap-x-[16px] gap-y-[10px]">

{legalLinks.map((link, i) => (

<HoverLine

key={link}

as="span"

text={link}

baseDelay={(bottomBase + 1 + i) * TEXT_STEP}

isInView={inView}

className="whitespace-nowrap text-[11px] uppercase text-white/40"

style={{ fontFamily: 'var(--font-mono-label)' }}

/>

))}

</div>

<div className="flex items-center justify-between">

<AnimatedLines

lines={['© 2026 processing.com. All rights reserved.']}

baseDelay={bottomBase * TEXT_STEP}

isInView={inView}

className="uppercase text-white/40"

style={{ fontFamily: 'var(--font-mono-label)', fontSize: 11 }}

/>

<motion.button

type="button"

aria-label="Back to top"

onClick={scrollToTop}

className="flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full bg-white/[0.09]"

{...popIn(inView, 130)}

>

<ArrowUp />

</motion.button>

</div>

</div>

</div>

</div>

</div>

</section>

)

}

export default function Footer() {

const canvas = useFitScale(DESIGN_WIDTH)

const contentRef = useRef<HTMLDivElement>(null)

const inView = useInView(contentRef, { once: true, amount: 0.2 })

const bottomBase = 5 + columns.length * ITEMS_PER_COLUMN

return (

<>

<section

ref={canvas.ref}

className="relative hidden w-full overflow-hidden bg-[#08090b] lg:block"

style={{ height: `calc(${DESIGN_HEIGHT * canvas.scale}px - ${FOOTER_TOP_TRIM_VH}vh)` }}

>

<div

className="absolute left-0"

style={{

top: `-${FOOTER_TOP_TRIM_VH}vh`,

width: DESIGN_WIDTH,

height: DESIGN_HEIGHT,

transform: `scale(${canvas.scale})`,

transformOrigin: 'top left',

}}

>

<div ref={contentRef} className="absolute" style={{ left: PAD_X, top: 0, width: CONTENT_WIDTH, height: DESIGN_HEIGHT }}>

<DrawInDividers isInView={inView} />

{/* logo + blurb */}

<div className="absolute flex items-center" style={{ left: 20, top: 195 }}>

<motion.img src={krakenMark} alt="" width={34} height={26} {...popIn(inView, 0)} />

<AnimatedLines

lines={['Kraken']}

baseDelay={0}

isInView={inView}

className="ml-[10px] text-[32px] font-medium text-white"

style={{ fontFamily: 'var(--font-logo)', letterSpacing: '-0.64px' }}

/>

</div>

<AnimatedLines

as="p"

lines={blurbLines}

baseDelay={1 * TEXT_STEP}

isInView={inView}

lineClassName="whitespace-nowrap"

className="absolute text-[16px] text-white/60"

style={{ left: 20, top: 256, width: 306, fontFamily: 'var(--font-logo)', letterSpacing: '-0.16px', lineHeight: '140%' }}

/>

{/* social icons */}

<div className="absolute flex items-center gap-[4px]" style={{ left: 20, top: 416 }}>

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 40)}

>

<img src={xIcon} alt="X" width={18} height={18} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 70)}

>

<img src={linkedinIcon} alt="LinkedIn" width={16} height={16} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

<motion.a

href="#"

className="group flex h-[36px] w-[36px] items-center justify-center rounded-[2px] bg-white/5 transition-colors duration-300 hover:bg-white/10"

{...popIn(inView, 100)}

>

<img src={githubIcon} alt="GitHub" width={16} height={16} className="transition-transform duration-300 group-hover:scale-90" />

</motion.a>

</div>

{/* link columns */}

{columns.map((col, i) => (

<FooterColumn key={col.header} header={col.header} x={col.x} links={col.links} colIndex={i} isInView={inView} />

))}

{/* bottom bar */}

<AnimatedLines

lines={['© 2026 processing.com. All rights reserved.']}

baseDelay={bottomBase * TEXT_STEP}

isInView={inView}

className="absolute uppercase text-white/40"

style={{ left: 20, top: 539, fontFamily: 'var(--font-mono-label)', fontSize: 12 }}

/>

<div className="absolute flex items-center gap-[16px]" style={{ left: 470, top: 539 }}>

{legalLinks.map((link, i) => (

<HoverLine

key={link}

as="span"

text={link}

baseDelay={(bottomBase + 1 + i) * TEXT_STEP}

isInView={inView}

className="whitespace-nowrap text-[12px] uppercase text-white/40"

style={{ fontFamily: 'var(--font-mono-label)' }}

/>

))}

</div>

<div

className="absolute flex cursor-pointer items-center gap-[16px]"

style={{ left: 1247, top: 535 }}

onClick={scrollToTop}

>

<HoverLine

as="span"

text="Back to top"

baseDelay={(bottomBase + 1 + legalLinks.length) * TEXT_STEP}

isInView={inView}

className="text-[12px] uppercase text-white/40"

style={{ fontFamily: 'var(--font-mono-label)' }}

/>

<motion.button

type="button"

aria-label="Back to top"

className="flex h-[27px] w-[27px] items-center justify-center rounded-full bg-white/[0.09]"

{...popIn(inView, 130)}

>

<ArrowUp />

</motion.button>

</div>

</div>

</div>

</section>

<MobileFooter />

</>

)

}
