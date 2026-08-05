"""
library.py — message copy only. No logic, no imports beyond BanditArm.
Add/edit message variants here; nothing else needs to change.
"""

from app.db.models import BanditArm

MESSAGE_LIBRARY = {
    BanditArm.cue: [
        "Little reminder: your body's probably ready for some water right about now.",
        "That afternoon slump might just be thirst wearing a different disguise.",
        "Dry mouth, dull focus, low energy. Nine times out of ten, that's just water talking.",
        "Before you reach for a snack, try water first. Sometimes that's the real ask.",
        "Your skin, your focus, your mood, all a little happier after a glass of water. React if you're actually going to do it, not just think about it 👀",
        "A quick pause: when's the last time you actually had a sip? Be honest, I'll know if you're lying.",
        "Sometimes the fix isn't more coffee. It's water. Prove me wrong, react.",
    ],
    BanditArm.habit_pairing: [
        "Making coffee anyway? Pour a glass of water first, it's basically free.",
        "Brushing your teeth tonight? Glass of water right after, no extra steps.",
        "Every time you check your phone today, let that be your cue to sip. I'm watching. Not really. But react anyway.",
        "Lunch break and water break go together better than you'd think.",
        "Right after your next meeting, ten seconds, one proper drink. React when it's done, I'm nosy.",
        "Sitting down at your desk? Water first, everything else after.",
        "Pair it with something you're already doing today. React with whatever you picked, I want to know.",
    ],
    BanditArm.log_prompt: [
        "How much water have you had today so far? React with your gut number, don't overthink it.",
        "Quick tally, where are you on your goal right now?",
        "Mind logging your last drink? Takes two seconds. I'll wait.",
        "Halfway through the day, how's the water count looking? No judgment. Okay, a little judgment.",
        "Curious where you're at. Send me a number, no pressure.",
        "Let's check in, how many glasses so far today? React or I'll assume it's zero.",
        "Just a number when you get a sec: how much water today?",
    ],
    BanditArm.carry_reminder: [
        "Heading out? Grab the water bottle on the way.",
        "Don't let it sit empty on the desk all day. That's a crime scene, not a water bottle.",
        "If it's not within reach, it's easy to forget it exists.",
        "Refill now so you're not caught thirsty later. React once it's full, I like proof.",
        "A bottle only helps if it's actually with you.",
        "Quick check, is your water bottle nearby right now? Be honest, react either way.",
        "Out the door? Bottle first, everything else second. Or don't, I'm a message, not a cop.",
    ],
    BanditArm.system_note: [
        "Just your regular hydration nudge for today.",
        "This is BlueDrop, checking in like we do.",
        "A gentle system reminder: water o'clock. React to confirm you've been notified, very official.",
        "Consider this your scheduled nudge to hydrate.",
        "Standing reminder from BlueDrop, how's the day going, hydration-wise?",
        "Nothing urgent, just a friendly nudge to drink up. React so I know this thing works.",
        "Your daily check-in: have you had water recently? No wrong answers, but there is a right one.",
    ],
    BanditArm.positive_association: [
        "You've been consistent lately, that adds up more than you'd think.",
        "Small sips, big difference. You're doing better than you realize.",
        "Proud of the streak you're building here. React so I can be smug about it.",
        "Every glass counts, and you've been showing up for yours.",
        "This is what taking care of yourself looks like. Keep at it.",
        "You're building a habit that'll outlast the reminder itself. React and let me feel useful.",
        "Nice work staying on top of this today. Or don't react, be mysterious about it, I respect it.",
    ],
}