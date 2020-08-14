
## Why you shouldn't use *bring*

In the interest of not wasting your time, nor mine, here's a list of reasons to help you decide whether *you* should or should not try out *bring*. I do hope this list will get shorter over time though, so maybe check back here every now and then if you are 'interested in principle'...  

## Missing features

- no hashes for downloaded files supported (yet)
- no support for secret values like passwords, access tokens, etc (yet)

### State of the code

Currently *bring* is in a late alpha state, I'd say. It's usable, and works most of the time, but you should expect some issues every now and then. Here are some of the things I'd like to fix before I'd consider releasing the first beta version:

- confusing or non-informative error messages
- documentation in general, but especially in-code
- test coverage of *bring* and it's dependencies
- pockets of complexity that turned out to be unnecessary, and should be removed or simplified
- startup time is not optimized yet at all. There should be some easy wins there, but not 100% sure.

### Design and technologies used

*bring* is written in object-oriented Python. It is -- some wil/might say -- over-engineered for what it is, with quite a few abstract class-hierarchies and other (arguable) 'anti-patterns' that could have been avoided if one was interested in more compact and maintainable code. I chose this design and its trade-offs deliberately, and am well aware of the disadvantages some of those decisions bring with them. *bring* is really only a side-product for a bigger application I have in mind, which is the main reason for most of kind of the decisions I mentioned. So, if a terse and minimal code-base with hardly any levels of abstractions is important to you, *bring* is most likely not for you...  

*bring* uses 'async'. A lot. That wasn't a deliberate decision when I started out, but I figured it can't hurt and since it's fully supported now... And then one thing lead to another, one 'async' function required the parent to also be 'async', and so on... So, after writing a lot of code I'm not so sure anymore whether I should have been more conservative and just use threading, or if the alternative would have been much worse, with race-conditions all over the place... Overall, I'm happy enough how the code turned out, so I'm not going to change anything now. And speed-wise I think *bring* does fairly well, for a Python application. But still, I can see how people could have strong opinions about something like this, so I thought I'd mention it.

Also, all the examples I use in the documentation show how package descriptions are written using *yaml*. I can't -- for the life of me -- figure out why; but some people out there seem to have a very strong aversion against *yaml*. I can only assume they used it in places where they shouldnn't have, or were forced to, or whatever. Anyway, if you have an opinion about 'yaml', don't use *bring*. It's just easier for both of us to not have to talk about something like this.

### License

*bring* uses a very strong copyleft license, [The Parity Public License](https://licensezero.com/licenses/parity). For now, anyway. Currently, I'm not sure how to best license *bring* (as that will also have implications on the bigger application I mention above), which is why I decided it makes the most sense to start with the 'strongest' possible license. It'll be easy to move to more permissive licenses later on. But if I start with something like the Apache license, or BSD, I won't be able to use a more restrictive license later on, at least not for the existing code.

You should read the license yourself, its a quick read and easy to parse. But in short: Parity only allows you to use code licensed with it in combination with software that is also licensed with Parity, or a license that is more permissive (which all 'standard' open source licenses are).

*Parity* is not technically 'open-source' itself, mainly because it discriminates against field of endeavor. The specific field of endeavor I want it to discriminate against is "using *bring* to create non-open source, commercial code". I find that fair enough, but am aware that there are some negative consequences, and there could be collateral damage that I do not intend to happen. I'd ask you to decide for yourself whether you also find that fair enough, and whether the consequences are acceptable or not. I welcome constructive feedback, but please keep it civil if you have some.

To remove most of the friction for people who want to use *bring* for personal use, *bring* is also licensed under the [Properity Public License](https://prosperitylicense.com/), which allows non-commerical usage.

For everyone else, I'll be offering private licenses for sale. Should there be any interest. Which I judge to be fairly unlikely, but who knows, it would be great if there was... Contact me.
