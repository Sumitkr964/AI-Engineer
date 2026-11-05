We want to make a coding agent which can solve simple bugs.
We will use the groq (MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
) llm for this. 

the llm will have some tools which will help in solving the bug.
One tool can be search files which lists path of files which are realated to the bug as per the llm.
we need search in file tool which can give line numbers releated to the bug
we need replace whilch allows the replacing a line with another line.

to test this, I wwant to test this myself. prepare a simple .cpp file and write boilerplate code in it. do not introduce any bug now,.
i will introduce the bug and test it mysekf,

I want to give the bug in simple english in cli and the llm and the tools should solve it.
meke the system without langgraph and keep it simple.
Also there will be max retry of 3 times. if the llm cant solve the bugs inside this limit it should restore and print a message saying that it cannot solve the bug.

also there should be clear print statements saying which tool was called at each steap. we want to understand the flow completely.
as soon as i change the cpp file and run the agent it should ask me my bug. after i give my bug, it should begin solving it.

do not write any test cases for now.
if anything is unclear, ask me.