# Transcript: Reinventing Entropy | Compression is Intelligence Part 1

https://www.youtube.com/watch?v=l6DKRf-fAAM · language `en` · WhisperX `medium` · generated 2026-11-17

Each line is one sentence: `[start → end] heat ✂ text`.

- **heat** is how much viewers rewatched that moment, from YouTube's most-replayed data (`▁` low to `█` highest). `·` means no heat data.
- **✂** means the picture cuts to a new shot during or just before that sentence.
- `###` lines are the creator's chapters.

## Most-replayed moments

1. 00:14:33 – 00:15:50 (peak 1.00)
2. 00:11:57 – 00:14:13 (peak 0.62)
3. 00:00:00 – 00:00:38 (peak 0.57)
4. 00:10:59 – 00:11:19 (peak 0.56)
5. 00:24:15 – 00:24:34 (peak 0.55)
6. 00:08:43 – 00:09:03 (peak 0.55)

## Transcript


### 00:00:00 On “Compression is intelligence.”

[00:00:00.1 → 00:00:04.5] ▅ When you encode text into binary, it's often nice to use as little data as possible.
[00:00:04.8 → 00:00:11.0] ▅ So you might naturally wonder, is there some kind of fundamental limit on how efficiently text can be compressed?
[00:00:11.6 → 00:00:14.5] ▅ The default encoding with ASCII is pretty inefficient.
[00:00:14.7 → 00:00:17.0] ▅ Each character is represented with eight full bits.
[00:00:17.4 → 00:00:25.1] ▄ If you apply a little cleverness associating more common characters with smaller bit strings, you can get this down to an average of around four bits per character.
[00:00:25.6 → 00:00:31.5] ▃ And then much smarter methods than that, that leverage patterns among long sequences of text, can get even better still.
[00:00:32.1 → 00:00:33.4] ▃ But again, what's the limit?
[00:00:34.3 → 00:00:37.9] ▃ I'm guessing many of you might have heard an estimate here, I will share one at the end.
[00:00:38.4 → 00:00:43.9] ▃ ✂ But much more interesting than any single numerical answer is how you would even approach answering it.
[00:00:44.3 → 00:00:50.1] ▂ This question dates back at least to the 1940s, with Claude Shannon's seminal work that kicked off information theory.
[00:00:50.6 → 00:00:59.0] ▂ ✂ Now what's very interesting is how the math that he developed to answer questions like this has turned out to be surprisingly useful for modern machine learning.
[00:00:59.6 → 00:01:12.1] ▂ ✂ To take the salient example of today, when large language models are trained, the pre-training portion of that is usually described as being about next-token prediction, specifically using something called cross-entropy loss.
[00:01:12.6 → 00:01:15.7] ▂ Now that term, cross entropy, has its roots in information theory.
[00:01:16.0 → 00:01:23.5] ▂ ✂ But what's also interesting is that one of the conclusions of information theory says that prediction and compression are mathematically equivalent.
[00:01:23.7 → 00:01:25.9] ▂ They turn out to be two sides of the same coin.
[00:01:26.4 → 00:01:38.1] ▂ ✂ Which means you can entirely reframe how you think about the pre-training objective as not really being about next token prediction per se, but instead as being about creating the most efficient possible text compressor.
[00:01:38.5 → 00:01:46.4] ▁ Later I'll explain exactly how that works, but when you do, I think it offers more clarity on what this notion of cross entropy really is and why you're using it.
[00:01:46.8 → 00:01:55.1] ▁ Also, I don't know about you, but to me at least, there's just something very intriguing about using compression as a fundamental objective while pursuing intelligence.
[00:01:55.6 → 00:01:59.6] ▁ ✂ In fact, some people have gone so far as to say, compression is intelligence.
[00:02:00.7 → 00:02:06.8] ▁ Now, as stated, that's a hard claim to judge rigorously, since intelligence is such a squishy and ill-defined term.
[00:02:07.0 → 00:02:13.7] ▁ The safer claim would be that the mathematical theory of compression is bizarrely relevant to artificial intelligence.
[00:02:14.2 → 00:02:24.2] ▁ ✂ Still, the pithy phrase is thought-provoking, so this is the first in a trilogy of videos aimed at laying down the mathematical fundamentals to assess what this claim is really getting at.
[00:02:25.0 → 00:02:36.2] ▁ ✂ For the next 30 minutes or so, you and I will be focused on understanding the limits of compression, and seeing if we can get you to feel like you could have rediscovered the core idea behind Shannon's Noiseless Coding Theorem.
[00:02:36.7 → 00:02:50.4] ▁ ✂ Doing so involves rediscovering a few key definitions, namely those of information and entropy, and it might sound a little weird for me to describe definitions as something to be discovered, but great definitions are often the residue of some kind of insight.
[00:02:51.0 → 00:02:58.6] ▁ See, these two specific terms are really not hard to define in the sense of laying down a formula for you, but doing so too early would spoil a good story.
[00:02:59.0 → 00:03:05.5] ▁ ✂ It is much more fun to see how you are inexorably drawn to them by asking about the limits of compressing language.
[00:03:06.0 → 00:03:15.9] ▂ And what I want you to notice by the end here is how we can't really answer this question, or at least Shannon couldn't, without necessarily engaging with some notion of intelligence.
[00:03:19.4 → 00:03:29.1] ▂ ✂ We will get to modeling language, which is wonderfully complicated, but it helps to warm up with a simpler example containing the same essential ideas needed for our path of rediscovery.

### 00:03:28 The warmup example

[00:03:29.8 → 00:03:35.5] ▂ ✂ Imagine you have a robot that we have sent to a faraway moon whose job is to wander the surface and collect data.
[00:03:36.1 → 00:03:41.7] ▂ ✂ From here on Earth, we send it instructions for how to move that are going to be limited to four very simple possibilities.
[00:03:42.2 → 00:03:46.3] ▂ Move up, down, left, or right, each one with a fixed step size.
[00:03:47.5 → 00:03:51.3] ▂ The nuance will be that these instructions are not uniformly distributed.
[00:03:52.0 → 00:03:59.7] ▂ ✂ Half of everything we send is up, one fourth of the instructions are down, one eighth are left, and the other eighth are right.
[00:04:00.4 → 00:04:08.0] ▂ ✂ It's a little contrived, it's meant to be a simple example, and in that spirit of simplicity we're also going to assume that every instruction is independent.
[00:04:08.2 → 00:04:11.9] ▂ ✂ They are sampled from this distribution regardless of the preceding context.
[00:04:12.7 → 00:04:28.5] ▂ ✂ When we send data to this bot far away, we're doing it as a stream of bits, ones and zeros, and it's very slow and costly to do that, so the natural question, the warm-up puzzle for you today, is to ask what is the most efficient possible way to encode these instructions as a stream of bits?
[00:04:29.6 → 00:04:37.6] ▁ ✂ And here, we might imagine three students who each attempt an answer, one who's straightforward, one who is clever, and one who is very theoretical.
[00:04:38.2 → 00:04:44.5] ▁ The straightforward student immediately raises their hand and says, well, for each of these four instructions, we could just use two bits.
[00:04:45.0 → 00:04:52.1] ▁ Maybe 00 encodes up, 01 encodes down, 10 encodes left, and 11 encodes right.
[00:04:52.8 → 00:04:56.0] ▁ ✂ On the receiving end, this makes it very easy for the robot to decode.
[00:04:56.4 → 00:05:01.8] ▁ It simply breaks up the bitstream into chunks of two and translates each chunk into the appropriate instruction.
[00:05:02.8 → 00:05:10.1] ▁ ✂ Now the clever student points out, well that does nothing to take advantage of the fact that up comes up way more frequently than left or right.
[00:05:10.7 → 00:05:14.8] ▁ ✂ They propose a method where we use a different number of bits for each instruction.
[00:05:15.2 → 00:05:25.5] ▁ ✂ I'll explain it in just a second, but I do want to call out the fact that as soon as you let different instructions get different numbers of bits, it's certainly not obvious that the robot is going to know how to decode it.
[00:05:26.3 → 00:05:29.7] ▁ ✂ After all, it needs to somehow know where to draw the dividing lines.
[00:05:30.6 → 00:05:36.6] ▁ Now, being very clever, the second student has thought that through, but it's easiest to explain if I just kind of lay it all out.
[00:05:37.2 → 00:05:46.8] ▁ ✂ What they suggest is letting the single bit zero represent up, letting the two bits one zero represent down, using one one zero for left and one one one for right.
[00:05:47.9 → 00:05:53.1] ▁ You can calculate the average number of bits per instruction that this would require with a simple weighted sum.
[00:05:53.6 → 00:06:00.1] ▁ Half the time only one bit is used, a quarter of the time two bits are needed, and the remaining times you need three bits.
[00:06:00.8 → 00:06:09.5] ▁ When you add this all up as a weighted sum, you get 1.75 bits per instruction, which is indeed better than the more naive approach of a flat two bits per instruction.
[00:06:10.1 → 00:06:20.3] ▁ The second student is spending more bits on those last two instructions, but because they come up so much less frequently, this is more than made up for by using only one bit for that most common instruction.
[00:06:21.1 → 00:06:23.6] ▁ ✂ And you can see this efficiency bear out empirically too.
[00:06:24.1 → 00:06:27.8] ▁ This right here is a set of instructions sampled from that distribution.
[00:06:28.2 → 00:06:33.4] ▁ ✂ You'll notice lots of ups, about half as many downs, and even fewer lefts and rights.
[00:06:34.1 → 00:06:42.3] ▁ When you turn each symbol into the appropriate bit string following this encoding, the resulting sequence of bits is indeed shorter than what the naive method gave.
[00:06:43.3 → 00:06:47.1] ▁ ✂ But I hear some of you asking, how does the robot know how to decode this?
[00:06:47.4 → 00:06:51.0] ▁ Can we be sure that there's an unambiguous way to draw the dividing lines?
[00:06:51.5 → 00:06:56.8] ▁ In the lingo of encodings, each of these four bit strings used to encode the instructions is called a code word.
[00:06:57.1 → 00:07:04.5] ▁ And as we step through things here, see if you can figure out what rule the clever student was following to make sure that their code words don't conflict with each other.
[00:07:05.6 → 00:07:10.7] ▁ And really, you just need to look at an example bitstream from the robot's perspective and think it through.
[00:07:11.4 → 00:07:14.0] ▁ Let's say that that very first bit that it receives is a 1.
[00:07:14.4 → 00:07:19.0] ▁ So far, this could be encoding any of the last three instructions, down, left, or right.
[00:07:19.6 → 00:07:27.5] ▁ If what follows is a 0, then it can only be down, there is no other possibility, so the robot can register that as a complete instruction.
[00:07:28.1 → 00:07:36.1] ▁ From there, starting fresh, if what follows is a zero, that must be encoding up, since there is no other possibility, nothing else starts with a zero.
[00:07:36.6 → 00:07:42.0] ▁ After that, if they see a one, this is so far ambiguous, it's the prefix for any of the last three code words.
[00:07:42.6 → 00:07:52.2] ▁ If the next bit is another one, it remains ambiguous, it's the prefix of the last two, but that following zero then makes clear these three bits must have been encoding left.
[00:07:53.0 → 00:08:02.4] ▁ In short, all the robot has to do is read in the next sequence of bits until the moment that it forms a complete code word, at which point it can register it as a complete instruction.
[00:08:04.0 → 00:08:11.3] ▁ If you step back and think about it, the key constraint for this all to work is that no codeword can be a prefix of another one.
[00:08:11.9 → 00:08:17.1] ▁ For example, let's say you tried to introduce some fifth instruction that had the codeword 100.
[00:08:17.6 → 00:08:26.3] ▂ That would cause conflict, because after reading 100, it's not clear whether that's supposed to be down or if it's supposed to be the start of this new fifth instruction.
[00:08:27.2 → 00:08:31.3] ▂ ✂ When you avoid this kind of conflict, an encoding method like this has a special name.
[00:08:31.5 → 00:08:33.9] ▂ It's known in the business as a prefix-free code.
[00:08:34.4 → 00:08:39.0] ▂ Or what is confusingly synonymous, it's actually more commonly known as a prefix code.
[00:08:39.5 → 00:08:46.8] ▃ ✂ And there's a really nice way to visualize choosing prefix-free codes with a certain diagram that represents every possible binary string.
[00:08:47.5 → 00:08:52.2] ▅ This diagram also has some helpful parallels with how I want to show entropy in just a few minutes.
[00:08:52.8 → 00:08:58.5] ▅ It's probably decently intuitive what's going on if you just pause and stare at it for a bit, but I'll call out the important features.
[00:08:59.6 → 00:09:02.4] ▅ Each layer shows every bit string of a given length.
[00:09:03.3 → 00:09:12.0] ▁ And you'll notice everything that starts with a 0 lives on the left half of this diagram, and everything that starts with a 1 lives on the right half of the diagram.
[00:09:12.5 → 00:09:15.6] ▁ And that same idea continues recursively as you go up.
[00:09:16.1 → 00:09:24.8] ▁ So everything starting with 0, 0 is above this quarter of the diagram, everything starting with 0, 1 is above this quarter of the diagram, and so on.
[00:09:25.6 → 00:09:32.6] ▁ In particular, the key property is that every binary string in this diagram is a prefix for everything that sits above it.
[00:09:33.8 → 00:09:49.8] ▁ ✂ So, when our clever student chose to allocate a single bit zero to represent the instruction up, they were effectively consuming half of the space of all possible code words by doing so, since everything starting with a zero is now prohibited based on this prefix-free property.
[00:09:50.7 → 00:09:59.0] ▂ Similarly, allocating one zero to down eats up another fourth of this space, and the remaining two instructions each eat up an eighth of the space.
[00:09:59.3 → 00:10:01.2] ▂ You can just see how nothing is left over.
[00:10:02.6 → 00:10:13.0] ▂ And at this point, I'm guessing that there's some bell kind of resonating in your mind, given that these proportions are all exactly the same as the probability for each instruction coming up.
[00:10:13.8 → 00:10:22.5] ▂ And in fact, that tickling sensation of a relationship between data size and probabilities is exactly the founding insight for information theory.
[00:10:23.2 → 00:10:31.3] ▂ When you stare at this pleasing alignment, it might suggest that the clever student solution is not just better, maybe it's somehow perfect.
[00:10:32.2 → 00:10:34.3] ▂ But at the moment, that feels like a bold claim to make.
[00:10:34.7 → 00:10:45.1] ▂ ✂ How could you know that there's not some ultra-clever method that does something fancy with really long sequences of instructions that somehow makes it so the average bits per instruction gets even lower than this?

### 00:10:46 What perfect compression looks like

[00:10:46.3 → 00:10:52.5] ▃ ✂ This takes us to the third student, Head in the Clouds, who has not really been thinking about actual codes that they can implement.
[00:10:53.0 → 00:10:57.9] ▃ They have been pondering what properties a perfect, optimally efficient code would have.
[00:10:58.7 → 00:11:10.1] ▄ ✂ They have this really clever idea, which is to argue that random noise should be incompressible, and therefore a perfect compression algorithm should produce a bitstream that's indistinguishable from random noise.
[00:11:10.7 → 00:11:16.7] ▅ What's neat is, even though that sounds kind of simple, this can actually lead you to reinventing the idea of Shannon entropy.
[00:11:17.4 → 00:11:25.6] ▄ Now when I say random noise, what I mean is that each bit is a 1 or a 0 with 50% probability, and all of the bits act independent from one another.
[00:11:26.1 → 00:11:30.7] ▃ It's not hard to show that our second student's encoding for the robot genuinely follows this rule.
[00:11:31.3 → 00:11:40.7] ▃ If you think about it, there's a 50% chance that the message starts with the instruction up, so that first bit has a 50% chance of being a 0, otherwise it's a 1.
[00:11:41.1 → 00:11:48.0] ▃ And then if it is a 1, there's a 50% chance that the instruction is down, meaning the next bit is 0, otherwise it's a 1.
[00:11:48.8 → 00:11:58.3] ▄ And so on, each new bit really does act like an independent coin flip, so to the receiver, that compressed bitstream really is indistinguishable from random noise.
[00:11:59.3 → 00:12:02.0] ▅ But why am I saying that random noise is incompressible?
[00:12:02.7 → 00:12:05.8] ▅ Well, for that, let's really focus on things from the receiver's perspective.
[00:12:06.3 → 00:12:15.2] ▅ And here, instead of thinking instruction by instruction, it helps to zoom out and frame our discussion in terms of entire messages and what the encoding for full messages looks like.
[00:12:15.7 → 00:12:19.7] ▅ when that receiver sees a string of n bits representing some compressed message.
[00:12:20.1 → 00:12:25.8] ▅ This is one out of 2 to the n possible messages they could have received that would have the same size.
[00:12:26.2 → 00:12:32.4] ▅ And then critically, because we're assuming this looks like random noise, all 2 to the n of those messages must be equally likely.
[00:12:33.1 → 00:12:36.2] ▅ Now to be clear, we're not just talking about the robot example anymore.
[00:12:36.7 → 00:12:52.4] ▅ Our theoretical head-in-the-cloud student really wants to make an argument for what perfect compression looks like for any data type, like maybe we're compressing language or compressing images, and they want an argument that works regardless of the details of what specific compression algorithm you're using.
[00:12:53.1 → 00:13:05.4] ▅ A loose intuition in your head is that maybe among all of the messages that compress down to n bits, some of them would contain a larger amount of predictable data, while others would have started as a smaller amount of unpredictable data.
[00:13:05.9 → 00:13:19.2] ▅ But the key point is that if the compressed bitstream really does look like random noise, meaning all of the bitstrings of size n are equally likely, it must be the case that all the underlying messages being compressed were equally likely to arise.
[00:13:19.6 → 00:13:26.4] ▄ ✂ and even more specifically with probability 1 over 2 to the n. So again, why am I claiming that this is incompressible?
[00:13:27.6 → 00:13:32.4] ▄ Well, let's pull up that same diagram representing the space of all possible binary strings.
[00:13:33.1 → 00:13:41.9] ▄ In this case, we can think of all the encodings for our 2 to the n equally likely messages as being the bit strings on one layer of this diagram.
[00:13:42.7 → 00:13:58.8] ▄ If you tried to define an alternate scheme, where you try to become more efficient by making one of these messages use fewer bits, it would move lower on the diagram, which means it then overlaps with some other message, so you would have to put that other message somewhere else in this diagram.
[00:13:59.3 → 00:14:08.9] ▄ At minimum, that means it's sharing a space with yet a third message, and those last two have to kind of get bumped up one layer, requiring that extra bit for each of them to disambiguate.
[00:14:09.4 → 00:14:13.1] ▄ So saving one bit over here costs you two bits elsewhere.
[00:14:13.4 → 00:14:17.9] ▃ You're basically pushing down a bump on the rug, only to see it pop up even worse in another spot.
[00:14:19.0 → 00:14:32.8] ▃ In general, any message encoded with a string lower on this diagram is going to be eating up more than its fair share of the space, which forces multiple other messages to occupy a smaller region, bumping them higher up, meaning they're encoded less efficiently.
[00:14:33.3 → 00:14:46.5] ▄ I'm going to guess that it's decently intuitive for everyone watching that the most efficient scheme here for equally likely messages is to give them all the same number of bits, but I do think the diagram gives a more concrete way to see why you end up with unfavorable trade-offs otherwise.

### 00:14:47 Defining information

[00:14:47.4 → 00:14:56.2] ▆ Once you have this idea that perfect compression looks like random noise, this is exactly the kind of thing I was referencing in the intro about how insights can lead you to definitions.
[00:14:56.9 → 00:15:20.9] █ Notice how what we're basically saying is that a message that uses n bits in a perfect scheme must have a probability of 1 over 2 to the n, or 2 to the negative n. If you take the log base 2 of both sides here and then negate, this is equivalent to saying that the number of bits allocated to a message, assuming perfect compression, is negative log base 2 of p, where p is the probability of occurring.
[00:15:22.4 → 00:15:27.5] █ ✂ This negative log expression is the fundamental formula for all of information theory.
[00:15:28.0 → 00:15:39.2] ▆ ✂ Everything up to this point is me trying to make this value feel like something you are inevitably drawn to by asking about perfect compression, rather than it feeling like some arbitrary definition that we start with.
[00:15:39.7 → 00:15:42.9] ▄ Some students do find this negative log takes a little getting used to.
[00:15:43.2 → 00:15:55.0] ▄ You know, it looks like it should be a negative value before you think about the fraction in the middle, but really the intuitive way to read it is that it's asking how many times do you chop your space of possibilities in half to get to a certain quantity.
[00:15:55.5 → 00:15:59.3] ▃ ✂ Here, let me pull up some axes and show you the graph of negative log of p.
[00:16:00.3 → 00:16:06.3] ▃ I've also seen some authors default to writing this as the log of 1 over p, which maybe you find more intuitive.
[00:16:06.7 → 00:16:14.3] ▃ You could also think of it as the log base 1 half of p, which I've never really seen anyone lean into, but personally I would be quite partial to that as a convention.
[00:16:14.9 → 00:16:21.9] ▃ Now, however you write it, what Shannon realized is that this is a very useful way to think about the information that a message contains
[00:16:22.3 → 00:16:30.9] ▃ even when literal perfect compression is not possible, and p is no longer a clean power of 2, which would mean that the output here is some fractional amount.
[00:16:31.3 → 00:16:35.5] ▃ In fact, he defined this expression to be the information of an event.
[00:16:36.3 → 00:16:48.9] ▂ The image I sometimes have in my head is to picture the probability of an event with a little pie chart, and the information is this bar above it that gets kind of pumped up to be taller as the probability is squeezed closer to zero.
[00:16:49.2 → 00:16:57.2] ▂ That is, unlikely messages contain a lot of information, and the bar is relaxed to get shorter as the probability approaches 100%.
[00:16:58.1 → 00:17:01.5] ▂ Highly expected messages contain very low information.
[00:17:01.9 → 00:17:04.9] ▂ I want to be clear that there is content to this definition.
[00:17:05.1 → 00:17:09.7] ▃ It's more than just rescaling probabilities, as if converting to an alternate unit system.
[00:17:10.3 → 00:17:11.7] ▃ You've already seen the core idea.
[00:17:12.1 → 00:17:19.2] ▃ ✂ In a perfect compression scheme, the number of bits allocated to a full message precisely equals this information content.
[00:17:19.6 → 00:17:22.2] ▃ Now, of course, perfect compression is not always possible.
[00:17:22.2 → 00:17:25.6] ▃ ✂ Your probabilities of messages are likely not perfect powers of two.
[00:17:26.1 → 00:17:35.6] ▃ So the more general way you would frame this is to say that the information of a message gives you a lower bound on how much it can be compressed, at least when you average over all possible messages.
[00:17:35.8 → 00:17:39.7] ▃ It's perfectly possible to overfit a compression algorithm to one specific case.

### 00:17:40 Information of language

[00:17:40.6 → 00:17:46.4] ▃ ✂ And to really wrap your mind around information and fractional bits, we need to step up our game beyond that warmup example.
[00:17:47.1 → 00:17:49.8] ▃ See, with the robot, the probabilities were overly clean.
[00:17:49.9 → 00:17:55.3] ▃ They were all perfect powers of two, so that the information per symbol could precisely match a whole number of bits.
[00:17:55.7 → 00:18:03.7] ▃ But Shannon was very interested in this question of limits on compression for much more realistic and complicated cases like natural language.
[00:18:04.1 → 00:18:12.5] ▃ For example, here I'll pull up the probabilities for each new letter in an example phrase, at least as determined by a little GPT that I'm running locally.
[00:18:13.2 → 00:18:21.5] ▄ And by the way, if the probabilities provided by a model feel like those might be distinct from the probabilities of actual language, you would be right to raise an eyebrow.
[00:18:21.8 → 00:18:22.6] ▄ Hold on to that thought.
[00:18:22.8 → 00:18:24.1] ▄ It becomes very relevant later.
[00:18:25.0 → 00:18:29.2] ▃ One key difference with language is how heavily dependent on context everything is.
[00:18:29.9 → 00:18:36.3] ▂ The probability distribution for each new letter you see is highly, highly contingent on everything that came before it.
[00:18:36.8 → 00:18:42.2] ▂ The other big difference is that all of these probabilities are obviously not going to be clean perfect powers of 2.
[00:18:42.7 → 00:18:50.7] ▂ So if you compute the Shannon information of each one of these, meaning you take the negative log base 2, all the numbers that you see are fractional amounts.
[00:18:51.2 → 00:18:55.2] ▂ And again, giving a vague interpretation of what these mean is really not hard.
[00:18:55.6 → 00:19:01.5] ▂ Information content is low for very predictable letters and it's high for very unpredictable letters.
[00:19:01.9 → 00:19:10.3] ▂ But all of you watching this are smart enough to demand a more exact interpretation, one that justifies why these values deserve to be given the units of bits.
[00:19:10.7 → 00:19:23.5] ▂ I mean, it's not like there's gonna be some perfect encoding where this letter i has a codeword that is somehow 4.19 bits, or where this highly predictable o is somehow encoded with just a narrow sliver of a bit.
[00:19:24.1 → 00:19:29.8] ▂ The real meaning is related to encoding entire messages and coming up with a bound on their compression.
[00:19:30.5 → 00:19:37.5] ▂ The probability for a full phrase, like the one I'm showing here, looks like multiplying the probabilities for each successive new letter.
[00:19:38.1 → 00:19:43.7] ▂ Where again, I'll emphasize that these successive letters' probabilities are conditioned on what came before.
[00:19:44.2 → 00:19:46.6] ▂ This is essentially the chain rule from probability.
[00:19:47.0 → 00:19:50.0] ▂ I want you to notice how nicely this plays with a logarithm.
[00:19:50.5 → 00:20:03.6] ▂ If you ask for the information of that full message, taking this negative log expression, because logarithms turn multiplication into addition, this breaks up really nicely as the sum of the information for each individual letter.
[00:20:04.1 → 00:20:12.6] ▂ In the final part of this trilogy, I'm going to walk you through a very specific compression algorithm that would actually compress this text to within one or two bits of this value.
[00:20:13.0 → 00:20:27.2] ▂ It's no longer as simple as mapping each character to a predefined codeword, but you nevertheless get this very direct sense of thinking about adding up the fractional information content of each letter to determine the length of the final encoding that you use.
[00:20:28.0 → 00:20:28.9] ▂ So that's the key idea.
[00:20:29.2 → 00:20:46.7] ▂ ✂ Even if by the time you need to relate this to actual data sizes, things will get rounded off to the nearest whole number, what Shannon realized is just how useful it is to work at this higher layer of abstraction where all your information is allowed to freely be continuous and information of successive events really nicely adds together.
[00:20:48.0 → 00:20:58.9] ▃ ✂ Still, if you step back and imagine yourself very seriously assessing the fundamental compressibility of language, all of this hinges on the question of how you know the probabilities for each successive letter.
[00:20:59.5 → 00:21:13.4] ▃ Here for all these animations, I've been illustrating things using a language model, but for one thing, that doesn't necessarily feel the same as the true probabilities underlying language, and for another, it's not even clear what we would mean by the true probabilities of language.
[00:21:14.2 → 00:21:23.4] ▃ ✂ So here I actually think it's most enlightening to take a step back in time and see how Shannon himself thought about all of this long before language models or modern data analysis.
[00:21:23.9 → 00:21:35.6] ▂ Some of his earliest experiments on the information of language involved looking at specific short sequences of characters, what you often hear referred to as n-grams, and then tracking the statistics of what tended to follow.
[00:21:36.1 → 00:21:49.3] ▂ So for example, if you scan through a few books and you notice every single time the two letters TH come up and you record what letters tend to follow, you could build up a table of those letters and let those statistics represent a sample for the probabilities you care about.
[00:21:50.0 → 00:21:58.5] ▂ Now the problem is that this just completely breaks down for longer strings of letters, most notably any string of text that never shows up in all of the books that you're analyzing.
[00:21:59.1 → 00:22:04.2] ▂ Nevertheless, it's perfectly reasonable to talk about what's expected to follow such a longer string.
[00:22:04.6 → 00:22:11.6] ▂ In fact, if anything, it's more important to talk about those cases, since longer context windows are when things are at their most predictable.
[00:22:12.1 → 00:22:15.7] ▂ And that's where you stand to get the most compression due to that predictability.
[00:22:16.6 → 00:22:24.0] ▂ So instead of using raw statistics, a little bit later Shannon analyzed a different model of the English language that he had available to him.
[00:22:24.7 → 00:22:25.5] ▂ His wife Betty.
[00:22:26.1 → 00:22:31.0] ▂ As the story goes, Shannon pulled out a book and began asking Betty to guess each next letter.
[00:22:31.5 → 00:22:33.9] ▂ Shannon would then transcribe her guesses letter by letter.
[00:22:34.5 → 00:22:42.2] ▃ Every time she guessed incorrectly, he wrote down the correct letter, and then whenever she guessed correctly, he would just replace it with a dash.
[00:22:43.0 → 00:22:53.4] ▃ The idea was that this transcribed version he was creating has fewer actual letters than the original, but his point was that it contained the same amount of information, at least in the following sense.
[00:22:53.9 → 00:23:01.8] ▂ If he could somehow obtain an exact replica of his wife and conduct the guessing game again, he would only need to supply her with this reduced text.
[00:23:02.3 → 00:23:08.6] ▂ These letters, by themselves, would provide just the right prompting for his duplicate wife to exactly reproduce the original.
[00:23:09.2 → 00:23:12.9] ▂ Of course, in practice, a person wouldn't necessarily guess the same way twice.
[00:23:13.5 → 00:23:20.6] ▁ And while this qualitatively conveyed the idea of predictability allowing for compression, it wasn't yet a measurement of information.
[00:23:21.0 → 00:23:25.6] ▁ A bit later still, in his 1950 paper Prediction and Entropy of Printed English,
[00:23:26.0 → 00:23:32.8] ▁ Shannon updated the experimental design to get a more robust read on this slippery question of the average information content in English.
[00:23:33.3 → 00:23:43.8] ▁ This time interviewing more people, instead of just logging whether each guess was right or wrong, Shannon recorded how many guesses were necessary for a human guesser to come up with the correct next letter.
[00:23:44.7 → 00:23:54.2] ▁ And then separately, he had this whole method for associating the number of guesses required with an implicit probability that a person would have been assigning to the true next letter.
[00:23:54.7 → 00:24:03.7] ▁ The details of that are a little bit in the weeds, but the broader point I want to make is how, in analyzing language, he wasn't just doing pure data analysis looking through books.
[00:24:04.1 → 00:24:09.6] ▁ He was trying to probe at an underlying model of language, namely the interviewee's brain.
[00:24:10.3 → 00:24:21.9] ▃ These brains that he could talk to were effectively treated as black boxes, ones with a sophisticated and yet indescribable understanding of language and an ability to predict characters based on the context.
[00:24:22.7 → 00:24:29.0] ▅ Now these days, in the 2020s, we have gone from merely interrogating black boxes that process language to designing them.

### 00:24:29 Defining Entropy

[00:24:29.9 → 00:24:42.7] ▄ ✂ The reason that you and I are here, revisiting the roots of information theory and this study of how compressible language is, is because of how much of the math in modern machine learning leverages the formulas that emerged in this field.
[00:24:43.2 → 00:24:50.5] ▂ Aside from the definition of information itself, there are three more key expressions that I want you to feel like you could have rediscovered.
[00:24:50.8 → 00:24:53.6] ▂ Not just because rediscovery makes them more memorable,
[00:24:54.1 → 00:25:04.6] ▃ but because seeing how they naturally arise from studying compression gives a more solid ground from which you can assess that thought-provoking interplay between compression and intelligence.
[00:25:05.1 → 00:25:09.2] ▃ ✂ You already have everything you need to reinvent the first of these, which is entropy.
[00:25:10.2 → 00:25:18.9] ▃ ✂ Imagine you have any signal that can be thought of as a sequence of symbols, whether that's the four robot instructions, the English language, or really anything else you dream up.
[00:25:19.5 → 00:25:34.6] ▄ Entropy asks about the average amount of information for each symbol, and then based on everything we've been discussing, where perfect compression looks like random noise, and how in that case, the number of bits used for a message is the same as the information content of that message,
[00:25:35.0 → 00:25:39.1] ▄ which again breaks down really nicely as the sum of the information of all the symbols.
[00:25:39.5 → 00:25:45.2] ▄ This question of measuring the average information per symbol is basically asking about the limit of compression.
[00:25:45.6 → 00:25:50.2] ▄ It would give you a lower bound on how efficiently a given signal could be compressed.
[00:25:51.0 → 00:25:59.7] ▄ ✂ And you and I already calculated this in one setting, when we took that weighted sum to find the average bits per instruction for the perfect encoding of the robot case.
[00:26:00.1 → 00:26:06.4] ▃ Basically, because that encoding was perfect, each symbol's codeword length is exactly the same as its information content.
[00:26:06.9 → 00:26:10.3] ▃ So effectively, we're calculating the average information per symbol.
[00:26:10.9 → 00:26:12.7] ▃ To generalize this, here's how that looks.
[00:26:13.1 → 00:26:27.9] ▃ For any given probability distribution, characterizing whatever symbols your messages are made out of, the average information per symbol should look like adding up p times the negative log of p for each probability p in that distribution.
[00:26:28.5 → 00:26:31.5] ▃ And take a moment to notice how we're visualizing this expression.
[00:26:32.0 → 00:26:42.2] ▂ Throughout the video, we've been picturing probability distributions with stacked horizontal bars, where each bar's width is equal to its probability, so altogether they add up to be 1.
[00:26:43.2 → 00:26:53.2] ▂ Now, above each one of those, I've put a rectangle whose height is locked to be the corresponding information value, the negative log base 2 of that probability.
[00:26:53.9 → 00:27:00.9] ▃ So the weighted sum up top, the average information per symbol, can be thought of as the total area of all these rectangles together.
[00:27:01.9 → 00:27:09.3] ▃ This is not yet fully general, it only describes the compression limit in cases where every new symbol follows some identical distribution.
[00:27:09.7 → 00:27:12.9] ▃ That's true in the robot case, but it's not true in English, for example.
[00:27:13.6 → 00:27:16.0] ▃ Nevertheless, it's important enough to deserve a name.
[00:27:16.6 → 00:27:22.4] ▃ ✂ And there's a fun story about how John von Neumann supposedly told Shannon that he should call this expression entropy.
[00:27:22.9 → 00:27:35.5] ▃ since for one thing, it resembles an expression already used for the idea of entropy in statistical mechanics, and for another, quote, nobody knows what entropy really is, so in an argument, you'll always have the advantage.
[00:27:35.9 → 00:27:39.8] ▃ I looked into it, it's probably apocryphal, but there seems to be a grain of truth to this.
[00:27:40.4 → 00:27:50.9] ▃ ✂ Now, whatever the true story is, Shannon did call this quantity entropy, and he denoted it with the letter H. And it's fun to take a moment to play around with this graphic to build a little intuition.
[00:27:51.5 → 00:27:56.3] ▂ The more evenly distributed a probability distribution, the higher the total entropy.
[00:27:56.8 → 00:28:09.7] ▂ Whereas if we squish things to become very uneven, maybe with one event dominating the probability space, this would have a very low entropy, since that one overwhelmingly probable event carries correspondingly little information.
[00:28:10.3 → 00:28:20.6] ▂ And then also, if you divide up the probability space even more, meaning it's distributed over more total possible symbols, each one has more information, so the total entropy is higher.
[00:28:21.1 → 00:28:31.1] ▂ And once more it's fun to kind of slosh everything around, where a very skewed distribution gives lower total entropy, whereas a more even spread gives us higher entropy.
[00:28:31.7 → 00:28:37.1] ▂ The vague qualitative intuition here is that entropy measures the amount of uncertainty in a distribution,
[00:28:37.6 → 00:28:49.6] ▂ But the more precise understanding, justifying why it deserves to be given in units of bits, is that it describes the minimum number of bits per symbol necessary to encode a message following this distribution.
[00:28:50.2 → 00:29:00.2] ▃ ✂ That statement, and everything we just covered, is more or less the content of a core theorem in Shannon's 1948 paper that kicked off information theory, the Noiseless Coding Theorem.
[00:29:00.7 → 00:29:09.5] ▂ ✂ It states that no encoding can ever be more efficient than this limit, and even more strongly he showed that it's always possible to get arbitrarily close to this limit.
[00:29:11.4 → 00:29:24.8] ▂ ✂ Now like I said, this expression only applies in cases where every symbol follows the same distribution, but Shannon was of course keenly interested in a more general setting, where the probabilities for each new symbol don't necessarily follow the same distribution.
[00:29:25.4 → 00:29:29.9] ▂ In particular, he spent a ton of time contemplating the compressibility of natural language.
[00:29:30.5 → 00:29:35.8] ▂ ✂ This requires a more general notion of entropy, something known as the entropy rate for a stochastic process.
[00:29:36.4 → 00:29:38.0] ▂ But it's the same basic question.
[00:29:38.3 → 00:29:40.4] ▂ What is the average information per symbol?
[00:29:40.9 → 00:29:44.5] ▂ Except in this case, we're now averaging over all possible messages.
[00:29:45.1 → 00:29:50.8] ▂ This is almost never a clean calculation that you can perform with some clean visual like the one we were just playing with.
[00:29:51.4 → 00:29:55.6] ▂ After all, what formula describes the probability distribution for language?
[00:29:56.2 → 00:30:06.0] ▂ ✂ So if you hear reference to the entropy of language, this is well beyond what any exact calculation can give you, hence why Shannon turned to estimates based on observation.
[00:30:06.4 → 00:30:13.2] ▂ And again, his methodology was not just data analysis, it's not some function that you can perform on a corpus of text.
[00:30:13.6 → 00:30:21.5] ▂ In order to get a satisfying estimate on compressibility, he found himself inevitably needing to probe at intelligent models of language.
[00:30:21.9 → 00:30:29.5] ▂ When his interviewees had at least 100 preceding letters of context, he estimated the entropy of English to be about 1 bit per character.
[00:30:29.9 → 00:30:38.1] ▂ This is a pretty wild number when you think about it, because it suggests that English could be compressed down to just a single yes or no answer for each character.
[00:30:39.0 → 00:30:50.4] ▂ ✂ Wild as that sounds, in the third part here I will show you that algorithm I've referenced where, if you're allowed to use a high quality language model for encoding and decoding, you can get surprisingly close to this limit in practice.
[00:30:51.2 → 00:30:60.0] ▂ ✂ Before then, it helps to understand a variation on entropy, known as cross entropy, asking both how and why it's used in training large language models,
[00:31:00.4 → 00:31:12.1] ▂ ✂ If you want to learn that, as well as a few fun related ideas like how large models are distilled into smaller ones, and why on earth GZIP can recover the structure between distinct languages, come join me in part two.

### 00:31:14 3b1b Talent

[00:31:14.5 → 00:31:24.9] ▂ ✂ Regular viewers will know that my new experiment for this year is to have a virtual career fair, a page at 3b1b.co slash talent, where this audience can explore aligned career opportunities.
[00:31:25.2 → 00:31:32.0] ▁ ✂ The meaningful update is just how much more content there is now, mainly in the form of featured interviews between me and the relevant teams.
[00:31:32.7 → 00:31:33.3] ▁ ✂ Here's my thinking.
[00:31:33.3 → 00:31:46.5] ▁ ✂ I feel like when you're assessing potential jobs, it's almost impossible to get a true sense of what it's like to work at a place just by poking around online, and you learn orders of magnitude more if you have a chance to sit down for lunch with a couple team members.
[00:31:46.8 → 00:31:49.4] ▁ My hope is to give you the vicarious version of that.
[00:31:50.0 → 00:31:55.3] ▁ ✂ So, if you're curious what I mean when I say these are all thoughtful and curious teams, go take a moment to explore.
[00:31:55.4 → 00:31:56.5] ▁ I really think you'll enjoy it.
