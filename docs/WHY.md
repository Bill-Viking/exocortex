# The soul of the operating system

*The models will change. The work, the memory, and the decisions should stay with us.*

I was walking home when a thought came to me: Exocortex is the soul of the operating system. The model is the body it thinks through.

I work across several projects, more than one computer, and different AI systems. The models can do impressive work. Keeping that work together is another matter. A conversation gets long. A session ends. I switch machines or use a different model. Then I become the person who has to remember where everything stands and explain it again.

There is something backwards about that. I am using a machine to help me manage complexity, and I end up carrying its continuity around in my head.

That is the problem I have been building Exocortex to address.

Its foundation is ordinary files. Each project has a record of where it stands, the decisions already made, and what needs to happen next. A session leaves an opener for the one that follows it. There are notes about how I work and rules I have explicitly agreed to. The next session is instructed to read those records before doing anything substantial.

When several sessions are working, they record who holds the writing responsibility and can send each other messages. A page I call the tree shows the projects and whose move comes next. That last part matters more than it might sound. If I cannot see where I left something, it is easy for that work to disappear from my attention even though every file is still on the disk.

This lets me finish a session with one model and continue with another. The next model reads the shared record. It has somewhere to begin.

The record can be incomplete or wrong. A model can misunderstand it. Those are real problems, and writing something into a file does not turn it into truth. But I can read that file, correct it, and carry it somewhere else. I can see what the machine is being told about me and my work.

That is the part I want to own.

There are already several approaches to this problem. [Basic Memory](https://github.com/basicmachines-co/basic-memory) keeps knowledge in readable Markdown files that people and AI systems can both use. Its hosted service also synchronizes that knowledge across devices. [agentBrain](https://github.com/frontmatters/agentBrain) gives different coding agents a shared collection of notes and offers an optional way for those agents to send messages to each other.

Other projects reach into the work itself. [memory-bank-skill](https://fockus.github.io/skill-memory-bank/) keeps project status, plans, and decisions in files that the next session can read. [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail_rust) gives agents mailboxes and lets them declare which files they intend to edit. Memory, handoffs, and coordination are already part of this field. Exocortex shares that ground.

Where I place Exocortex is around the person moving among all those projects. I want to see what is unfinished across my work, know which session is responsible for each piece, and return on another machine without having to assemble the story again. The project records, rules, messages, and tree are meant to serve that daily habit. Someone whose main need is searchable notes may already have enough in a memory tool. My need is to keep the whole of my working life in view.

The more I work this way, the less I think the important question is which company makes the model. Models differ, and those differences matter. Some are better at a particular job. Some cost too much to use for everything. I want to be able to choose without having to reconstruct my working life each time.

Exocortex gives that life a place outside any one conversation. The model supplies the reasoning while it is running. The written record carries what I have chosen to keep. I remain responsible for deciding whether the work is any good and where it is meant to go.

That is what I was getting at with the soul and the body. The continuity should survive a change of machinery.

It also changes how I think about the operating system.

For a long time, choosing a computer has meant choosing a world. Its applications, its accounts, its habits, its way of keeping your things. You learn how to live there. Over the years you accumulate enough inside it that leaving becomes a project of its own.

I think a personal layer like this could become the place we actually work from. I would tell it what I am trying to do, and it would help me use the appropriate tools. My history with it would continue across those tools. Moving to another machine would be a change of equipment within the same working life.

There would still be an operating system underneath. Hardware needs managing. Files need storing. Permissions and security do not disappear because I can talk to a computer. The change I am interested in is where the relationship lives, and who gets to control it.

Standards such as the [Model Context Protocol](https://modelcontextprotocol.io/) offer one part of that arrangement: a common way for AI applications to connect to tools and data. A connection standard cannot settle who owns the information or who is allowed to use it. It does make it easier to build an interface that reaches beyond one application's walls.

I expect companies such as Microsoft and Apple to keep making useful software. Their formats and services may be with us for decades. But I can imagine their place in my life changing. I might use a company's tools because they do a job well, while the personal environment through which I use them belongs to me.

They would have to compete for that job. Leaving one service would no longer mean leaving so much of myself behind.

That is the end of the software companies' tyranny I have in mind: the power they gain from making departure difficult. I am quite happy to pay for something useful. I want the freedom to stop paying for it without losing the history that made it useful to me.

There is an obvious danger here. The AI company could become the new landlord.

If one assistant holds my memory, understands my projects, and controls access to everything I use, moving away from it could become harder than switching computers ever was. A friendly conversational interface could make that dependence feel personal. We could end up more attached to the company that holds the record because it appears to know us.

So ownership has to mean something practical. I need to be able to take the record with me in a form another system can actually use. I need to be able to correct it and decide what belongs in it. Changing models should be a choice I can make while the work continues.

Keeping files on my own machine is part of that. It does not make every interaction local: when I use a hosted model, the material I send it goes to that provider. The choice of what to share remains part of the design. A private record is only useful if I can control how it is used.

Exocortex is available under the Apache 2.0 licence. My personal record does not ship with it; someone else begins with their own. It is early software, built around coding agents, and its checks are further along on macOS than on Windows. There is work left to do.

But the direction is clear to me. I want my computer to meet me where I left off. I want to spend less of my time reminding software what my life is about. And I want the history we build together to remain mine when a better tool comes along.

The operating system of my working life should belong to me. The companies should compete to provide its tools.

The author also writes at [What We Make of Things](https://whatwemakeofthings.substack.com/), where this essay will appear.
