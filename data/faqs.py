"""Shared FAQ data for BgClear content pages.

Entries are plain-text (or minimal HTML) Q&A pairs. Consumers (pagegen
script generation) render them into <details> blocks and FAQPage JSON-LD.

Each entry: key -> dict(q, a). The 'a' value is the plain text used in
FAQPage schema; visible rendering wraps it in a <p>.
"""

FAQS = {
    "mobile-removebg": {
        "q": "Can I use a background remover on my phone?",
        "a": "Yes. BgClear works in any mobile browser — drag or tap to select a photo, and the model runs locally on your device, so it also works on a weak connection. There's no app to install and no account to create.",
    },
    "make-png-transparent": {
        "q": "How do I make a PNG transparent?",
        "a": "Open the image in BgClear and export as PNG. PNG is the format that supports transparency, so always choose the PNG export (not JPG) when you need a transparent background.",
    },
    "jagged-cutout": {
        "q": "Why does my cutout look jagged?",
        "a": "Jagged edges usually come from low-contrast edges or a busy background. Re-shoot with better lighting and a background that contrasts with the subject, then zoom in to touch up problem edges. AI output on clean, well-lit photos is generally smooth.",
    },
    "no-upload": {
        "q": "Are my images uploaded to a server?",
        "a": "No. BgClear processes images entirely in your browser — the files never leave your device, so there is nothing for us to store, log, or sell.",
    },
    "commercial-use": {
        "q": "Can I use BgClear for commercial work?",
        "a": "Yes. There are no restrictions on commercial use of images you process with BgClear, no watermark, and no license fee.",
    },
    "formats": {
        "q": "What image formats are supported?",
        "a": "JPG, PNG, and WebP in, and transparent PNG or white-filled JPG/PNG/WebP out. GIF and other formats should be converted to PNG first.",
    },
    "white-vs-transparent": {
        "q": "White or transparent background: which should I use?",
        "a": "Use white for marketplaces, passports, IDs, and print. Use transparent PNG when the image will sit on a website or design that has its own background, such as a logo on a colored header.",
    },
}
