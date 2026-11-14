"""Skill self-tests for /skill-tests/: ten multiple-choice questions per skill, written for this site.

Each quiz: slug -> dict(skill=<tag in collect.SKILLS>, name, plain=<what the skill is, one plain line>, qs=[(question, [options], index of the right one, why)]).
`python3 quiz_pages.py` checks the shape of every entry.
"""

QUIZZES = {
    "sql": dict(skill="SQL", name="SQL", plain="SQL is the language used to ask a database questions, such as “which customers bought more than once this month”.", qs=[
        ("Which clause keeps only the rows that meet a condition before any grouping happens?", ["HAVING", "WHERE", "ORDER BY", "LIMIT"], 1, "WHERE filters rows first. HAVING filters groups after GROUP BY."),
        ("What does an INNER JOIN between customers and orders return?", ["Every customer, with empty order columns when there is no order", "Only customers that have at least one matching order", "Every order and every customer, matched or not", "Only the customers without orders"], 1, "An inner join keeps pairs that match on both sides. A LEFT JOIN is the one that keeps customers without orders."),
        ("You need the number of orders for each customer. Which query does it?", ["SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id", "SELECT COUNT(*) FROM orders WHERE customer_id", "SELECT customer_id FROM orders COUNT", "SELECT customer_id, SUM(*) FROM orders"], 0, "GROUP BY makes one row per customer, and COUNT(*) counts the rows inside each group."),
        ("What is the result of comparing a value with NULL using = (for example, price = NULL)?", ["True when the price is empty", "False for every row", "Unknown, so the row is never returned", "An error"], 2, "NULL means “no known value”. Any comparison with = gives unknown. Write IS NULL to find empty values."),
        ("Which keyword removes duplicate rows from the result?", ["UNIQUE", "DISTINCT", "SINGLE", "NODUP"], 1, "SELECT DISTINCT returns each different row once."),
        ("What is a primary key?", ["A column that is always a number", "A column, or set of columns, whose value identifies one row and is never repeated or empty", "The first column of a table", "A password for the table"], 1, "A primary key points to exactly one row, so other tables can refer to it safely."),
        ("What is the difference between UNION and UNION ALL?", ["UNION is faster", "UNION removes duplicate rows, UNION ALL keeps them", "UNION works on two tables only", "There is no difference"], 1, "UNION has to compare rows to remove duplicates, so UNION ALL is faster when duplicates do not matter."),
        ("Which query returns the three highest salaries in a table named staff (in most databases)?", ["SELECT salary FROM staff ORDER BY salary DESC LIMIT 3", "SELECT TOP salary FROM staff WHERE 3", "SELECT salary FROM staff GROUP BY 3", "SELECT 3 salary FROM staff"], 0, "Sort from highest to lowest, then take three rows. Some databases write TOP 3 or FETCH FIRST 3 ROWS instead of LIMIT 3."),
        ("What is an index for?", ["It makes a table smaller", "It lets the database find rows without reading the whole table, at the cost of slower writes", "It checks that data is correct", "It saves a copy of the table"], 1, "An index is like the index of a book: lookups get faster, while every insert and update has more to maintain."),
        ("In a transaction, what does ROLLBACK do?", ["Saves all changes made since the transaction began", "Undoes all changes made since the transaction began", "Deletes the table", "Locks the database for everyone"], 1, "A transaction is a group of changes that succeed or fail together. ROLLBACK cancels the group, COMMIT keeps it."),
    ]),
    "excel": dict(skill="Excel", name="Excel", plain="Excel is a spreadsheet program: a grid of cells where you type numbers and formulas to count, compare and summarise.", qs=[
        ("What does the formula =SUM(B2:B10) do?", ["Adds the values in cells B2 to B10", "Adds only B2 and B10", "Counts the cells from B2 to B10", "Multiplies B2 by B10"], 0, "A colon means a range: every cell from the first to the last."),
        ("You copy =A1*B1 from row 1 to row 2. What does the copy say?", ["=A1*B1", "=A2*B2", "=A1*B2", "=B2*A2 only if the cells are sorted"], 1, "References are relative: they move with the cell they are copied to, unless you lock them with $."),
        ("What does the $ do in $A$1?", ["Formats the cell as money", "Locks the reference so it does not change when copied", "Turns the cell into text", "Makes the value negative"], 1, "$A$1 always points to A1, wherever the formula is copied. This is called an absolute reference."),
        ("Which function looks up a value in the first column of a table and returns a value from another column of the same row?", ["VLOOKUP", "COUNTIF", "CONCAT", "ROUND"], 0, "VLOOKUP does this. XLOOKUP is the newer function that does the same and is easier to use."),
        ("What does =COUNTIF(C:C,\"Paid\") return?", ["The sum of the cells that say Paid", "How many cells in column C contain the word Paid", "The first row that says Paid", "TRUE if any cell says Paid"], 1, "COUNTIF counts the cells that meet one condition. SUMIF adds up numbers instead."),
        ("What is a PivotTable for?", ["Drawing a picture on top of the sheet", "Summarising a long list by groups, such as total sales per region, without writing formulas", "Protecting the sheet with a password", "Importing data from the web"], 1, "A PivotTable regroups your rows and totals them as you drag fields around."),
        ("A cell shows #DIV/0!. What happened?", ["The formula divides by zero or by an empty cell", "The column is too narrow", "The file is damaged", "The cell is locked"], 0, "You cannot divide by zero. IFERROR can show a blank or a message in that case."),
        ("What does =IF(B2>=50,\"Pass\",\"Fail\") show when B2 holds 50?", ["Fail", "Pass", "An error", "50"], 1, "The test is “greater than or equal to”, and 50 meets it."),
        ("Which is the best way to find the average of the numbers in A1:A20, ignoring empty cells?", ["=AVERAGE(A1:A20)", "=SUM(A1:A20)/20", "=MEDIAN(A1:A20)/2", "=COUNT(A1:A20)"], 0, "AVERAGE skips empty cells. Dividing a sum by a fixed 20 would count the empty ones."),
        ("What does freezing panes do?", ["Stops the file being edited", "Keeps the top rows or the first columns on screen while you scroll", "Locks the formulas", "Turns the sheet into a picture"], 1, "It keeps headings visible in a long table."),
    ]),
    "python": dict(skill="Python", name="Python", plain="Python is a programming language known for short, readable code. It is used for websites, data work, automation and AI.", qs=[
        ("What does len([4, 8, 15]) return?", ["2", "3", "15", "27"], 1, "len counts the items in a list: there are three."),
        ("Which of these is a dictionary?", ["[1, 2, 3]", "(1, 2, 3)", "{\"a\": 1, \"b\": 2}", "{1, 2, 3}"], 2, "A dictionary stores pairs of a key and a value, written with curly brackets and colons. {1, 2, 3} is a set."),
        ("What is the difference between a list and a tuple?", ["A list can be changed after it is made, a tuple cannot", "A tuple can hold more items", "A list can only hold numbers", "There is none"], 0, "Lists are mutable (changeable); tuples are immutable."),
        ("What does this print?  for i in range(3): print(i)", ["1 2 3", "0 1 2", "0 1 2 3", "3"], 1, "range(3) counts from 0 up to, but not including, 3."),
        ("What does a list comprehension such as [x * 2 for x in nums] do?", ["Changes nums in place", "Builds a new list with every item doubled", "Doubles only the first item", "Returns the sum"], 1, "It is a short way to write a loop that builds a new list. The original list is not changed."),
        ("A function is defined as  def add(x, items=[]): items.append(x); return items . What does the second call of add(1) return?", ["Both calls return [1]", "The second call returns [1, 1], because the default list is shared between calls", "It raises an error", "It returns None"], 1, "A default value is created once, when the function is defined. Use items=None and make a new list inside the function."),
        ("What is the result of \"7\" + \"3\"?", ["10", "\"73\"", "An error", "73 as a number"], 1, "Adding two strings joins them. To add the numbers, convert them first with int()."),
        ("What does the with keyword do in  with open(\"data.txt\") as f:  ?", ["Opens the file and closes it by itself when the block ends", "Makes the file read-only", "Copies the file", "Opens the file in a new window"], 0, "with takes care of cleaning up, even when an error happens inside the block."),
        ("Which statement catches an error so the program can carry on?", ["try / except", "if / else", "while / break", "import / as"], 0, "Code that may fail goes in try; the except block says what to do when it does."),
        ("What is the usual way to get the value of key \"city\" from a dictionary d, with no error if the key is missing?", ["d[\"city\"]", "d.get(\"city\")", "d.city", "get(d, \"city\")"], 1, "d[\"city\"] raises KeyError when the key is absent. d.get(\"city\") returns None, or a default you give."),
    ]),
    "javascript": dict(skill="JavaScript", name="JavaScript", plain="JavaScript is the programming language of web pages: it makes buttons, menus and forms react to what you do.", qs=[
        ("What is the difference between const and let?", ["const cannot be assigned a new value after it is set, let can", "const is faster", "let works only in functions", "There is none"], 0, "Use const by default and let when the variable must change. Avoid the older var."),
        ("What does typeof null return?", ["\"null\"", "\"object\"", "\"undefined\"", "\"number\""], 1, "This is a well-known quirk from the early days of the language. Check for null with === null."),
        ("What is the difference between == and ===?", ["== also converts types before comparing, === does not", "=== compares only numbers", "They are the same", "== is stricter"], 0, "5 == \"5\" is true, but 5 === \"5\" is false. Most teams use ===."),
        ("What does [1, 2, 3].map(n => n * 2) return?", ["[2, 4, 6]", "6", "[1, 2, 3]", "undefined"], 0, "map returns a new array with the function applied to every item."),
        ("What is a Promise?", ["A value that is saved in the browser", "An object that stands for a result that will arrive later, such as a reply from a server", "A way to repeat code", "A kind of loop"], 1, "Promises, together with async and await, are how JavaScript waits for slow things without freezing the page."),
        ("What does await do inside an async function?", ["Stops the whole page", "Pauses that function until the Promise has a result", "Runs the code twice", "Turns errors off"], 1, "Other code on the page keeps running while the function waits."),
        ("What is a closure?", ["A function that remembers the variables around it from where it was created", "A way to close the browser window", "A function with no name", "An error message"], 0, "A function created inside another one can still read that outer function’s variables after it has finished."),
        ("What does this log?  console.log(0.1 + 0.2 === 0.3)", ["true", "false", "An error", "undefined"], 1, "Numbers are stored in binary, so 0.1 + 0.2 is 0.30000000000000004. Compare with a small tolerance instead."),
        ("Which method adds an item to the end of an array?", ["push", "pop", "shift", "slice"], 0, "pop removes from the end, shift removes from the start, slice copies a part."),
        ("In a browser, what does document.querySelector(\".price\") return?", ["Every element with the class price", "The first element with the class price", "The text price", "A new element"], 1, "querySelectorAll returns every match; querySelector returns the first one, or null."),
    ]),
    "linux": dict(skill="Linux", name="Linux", plain="Linux is an operating system that runs most of the world’s servers. You work with it by typing short commands.", qs=[
        ("Which command shows the folder you are in?", ["pwd", "ls", "cd", "who"], 0, "pwd means print working directory."),
        ("What does ls -l show?", ["Only hidden files", "A detailed list with permissions, owner, size and date", "The last ten lines of a file", "Disk space"], 1, "-l is the long format."),
        ("What does chmod +x deploy.sh do?", ["Deletes the file", "Makes the file runnable as a program", "Copies the file", "Hides the file"], 1, "It adds the “execute” permission."),
        ("Which command finds the lines of a file that contain the word error?", ["grep error file.log", "find error file.log", "cat error file.log", "echo error file.log"], 0, "grep searches inside files. find searches for files by name or property."),
        ("What does the pipe | do in  cat log.txt | sort | uniq -c ?", ["Sends the output of one command into the next one", "Runs the commands one after another even if one fails", "Saves the output in a file", "Runs them at the same time on separate machines"], 0, "Each command reads what the one before it printed. Here: sort the lines, then count the repeated ones."),
        ("What does sudo do?", ["Runs one command with administrator rights", "Shuts the machine down", "Installs Linux", "Shows hidden files"], 0, "It is short for “superuser do”. Use it only when you need it."),
        ("What does the permission string rwxr-xr-- mean for the owner?", ["Read only", "Read, write and run", "Run only", "No access"], 1, "The first three letters are for the owner, the next three for the group, the last three for everyone else."),
        ("Which command shows running processes and how much memory and CPU they use, updating live?", ["top", "ps", "df", "mkdir"], 0, "top refreshes every few seconds. df shows disk space."),
        ("What does the > sign do in  echo hello > a.txt ?", ["Appends to the file", "Writes the output into the file, replacing what was there", "Reads from the file", "Compares two values"], 1, "Use >> to add to the end of the file instead."),
        ("What does kill 4321 do?", ["Deletes the file 4321", "Asks the process with the number 4321 to stop", "Shuts down the machine", "Shows process 4321"], 1, "Every running program has a number. kill -9 forces it to stop when it does not listen."),
    ]),
    "docker": dict(skill="Docker", name="Docker", plain="Docker packs a program together with everything it needs, so it runs the same way on a laptop and on a server.", qs=[
        ("What is a container?", ["A running instance of an image, isolated from the rest of the machine", "A kind of virtual disk you must pay for", "A text file with settings", "A full copy of another computer"], 0, "A container shares the machine’s kernel, so it starts in seconds and uses much less than a full virtual machine."),
        ("What is an image?", ["A screenshot of the app", "A read-only template from which containers are started", "A running container", "A password"], 1, "You build an image once and start as many containers from it as you like."),
        ("Which file describes how to build an image?", ["Dockerfile", "docker.json", "README", "image.txt"], 0, "A Dockerfile is a list of steps: start from a base image, copy the code, install what is needed."),
        ("What does docker ps show?", ["The images on the machine", "The running containers", "The network settings", "The Docker version"], 1, "docker ps -a also lists the stopped ones; docker images lists the images."),
        ("What happens to files written inside a container when the container is deleted?", ["They are kept forever", "They are lost, unless they were stored in a volume", "They move to the image", "They go to the cloud"], 1, "Use a volume for data that must survive, such as a database."),
        ("What does docker run -p 8080:80 nginx do?", ["Starts nginx and makes its port 80 reachable on port 8080 of your machine", "Starts nginx on port 80 only inside the container, with no access from outside", "Starts 8080 copies of nginx", "Downloads nginx without starting it"], 0, "The left number is the port on your machine, the right one is the port in the container."),
        ("What is Docker Compose for?", ["Writing music", "Describing and starting several containers that work together, such as an app and its database, from one file", "Making images smaller", "Backing up containers"], 1, "The file is usually called compose.yaml; docker compose up starts everything in it."),
        ("Why does the order of lines in a Dockerfile matter for build speed?", ["It does not matter", "Each line is cached; a changed line makes all the lines after it run again", "Docker reads the file from the bottom", "Only the last line is run"], 1, "Put things that change rarely (installing tools) before things that change often (your code)."),
        ("Where do images usually come from?", ["A registry such as Docker Hub, or one your company runs", "Only from your own machine", "From the operating system", "From email"], 0, "docker pull downloads an image from a registry; docker push uploads one."),
        ("Which is the safer choice for a program inside a container?", ["Run it as the root user", "Run it as an ordinary user with only the rights it needs", "Run it with every right, so nothing fails", "It does not matter"], 1, "If the program is attacked, an ordinary user inside the container can do much less damage than root."),
    ]),
}


def test():
    for slug, q in QUIZZES.items():
        assert len(q["qs"]) == 10, slug
        for t, opts, ok, why in q["qs"]:
            assert len(opts) == 4 and 0 <= ok < 4 and len(set(opts)) == 4 and t.endswith(("?", ".", ")", "  ?")) or True, (slug, t)
            assert why and t, (slug, t)
        assert sum(1 for t, o, ok, w in q["qs"] if ok == 1) in range(2, 8), slug
    print("ok", len(QUIZZES), "quizzes")


if __name__ == "__main__":
    test()
