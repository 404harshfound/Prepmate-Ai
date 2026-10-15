-- Seed question bank: ~40 questions across four round types and three
-- difficulty levels. Reference answers follow the STAR pattern where
-- applicable (HR, behavioural) and give a model solution for technical
-- and aptitude.
--
-- These are written for Indian placement interviews: campus rounds,
-- off-campus drives, service-company panel interviews.

insert into app.questions (round_type, topic, difficulty, prompt, reference_answer, source) values

-- ===================== HR (10) =====================

('hr', 'self-introduction', 1,
 'Tell me about yourself.',
 'Situation: I am a final-year Computer Science student at XYZ University with a CGPA of 8.5. Task: Over the past year I focused on building full-stack skills through internships and personal projects. Action: I interned at a mid-sized SaaS company where I built an internal dashboard using React and Django, reducing report-generation time by 40%. I also led a four-person team for our capstone project, an ML-powered resume screener. Result: These experiences taught me to ship working software under deadlines and collaborate across teams, which is exactly why I am excited about this role.',
 'Common HR opener'),

('hr', 'strengths-weaknesses', 1,
 'What are your strengths and weaknesses?',
 'Situation: In every team project at university I naturally end up organising the timeline. Task: For our database-systems course project we had three weeks and four members with clashing schedules. Action: I broke the work into daily milestones and ran ten-minute stand-ups. Strength: my ability to keep a team on track. Weakness: I tend to spend too long reviewing code before committing. I have been setting myself time-boxed review windows of 15 minutes to manage this. Result: Our project was the only one submitted on time with full test coverage.',
 'Common HR question'),

('hr', 'why-this-company', 2,
 'Why do you want to work for our company?',
 'Situation: I have been following your engineering blog for the past year, especially the series on scaling microservices. Task: I wanted to understand how companies handle millions of transactions reliably. Action: I replicated your pub-sub architecture in a personal project and benchmarked it against a monolith. Result: The experience showed me your team solves the exact class of distributed-systems problems I want to work on, and your mentorship culture will accelerate my growth as an engineer.',
 'Common HR question'),

('hr', 'career-goals', 2,
 'Where do you see yourself in five years?',
 'Situation: Right now I am a generalist who can build both frontends and APIs. Task: Over five years I want to develop deep expertise in backend systems design. Action: In years one and two I plan to master the tools and domain of whichever team I join, then take on ownership of a service or module. By year three or four I would like to mentor junior engineers. Result: In five years I see myself as a senior engineer who can design a system end to end and help newer team members grow, exactly the path your engineering ladder supports.',
 'Common HR question'),

('hr', 'conflict-resolution', 2,
 'Tell me about a time you had a disagreement with a teammate.',
 'Situation: During our capstone project my teammate wanted to use MongoDB for what was clearly relational data. Task: I needed to resolve this without creating bad blood because we had ten weeks left together. Action: I set up a thirty-minute comparison where we both modelled the same three queries in Mongo and Postgres. The joins were three times simpler in SQL and his aggregation pipeline had a bug. I let the code speak instead of arguing. Result: He agreed to use Postgres, and later thanked me for the structured comparison. We shipped on time.',
 'Behavioural-style HR question'),

('hr', 'handling-pressure', 2,
 'How do you handle pressure or tight deadlines?',
 'Situation: Two days before my internship demo, the staging server crashed and we lost the deployment. Task: I had to rebuild, re-deploy and rehearse the demo in 48 hours. Action: I prioritised the three features the stakeholders cared about, wrote a quick Docker-compose setup so I could deploy locally as a fallback, and practised the demo twice on camera. Result: The demo went smoothly, the CTO complimented the recovery, and I now always keep a one-command local deploy ready.',
 'Common HR question'),

('hr', 'teamwork', 1,
 'Do you prefer working alone or in a team?',
 'Situation: I have done both — solo side-projects and team hackathons. Task: The question is really about adaptability. Action: When I am prototyping a new idea I like working alone because I can move fast and explore freely. But for anything that ships to real users I prefer a team because code review, diverse thinking, and shared ownership produce better software. Result: At my internship I paired with a senior developer for the trickiest module and delivered it two days early. I see teamwork and independent work as tools I pick based on the stage of the project.',
 'Common HR question'),

('hr', 'salary-expectations', 3,
 'What are your salary expectations?',
 'Situation: As a fresher I am aware that my primary gain from the first job is learning and mentorship, not compensation. Task: I want to answer honestly without underselling myself. Action: Based on my research of industry standards for this role and location, and considering the skills I bring, I am open to a package in the standard band your company offers for this position. I would value learning opportunities, a strong team, and growth potential alongside fair compensation. Result: I am flexible and happy to discuss a number that works for both sides once I understand the complete benefits.',
 'Sensitive HR question'),

('hr', 'relocation', 1,
 'Are you willing to relocate?',
 'Situation: I am currently based in [city] and have lived in hostels through college, so I am comfortable moving. Task: The company may need me in a different city. Action: I am fully open to relocating wherever the team is based. I see it as a chance to experience a new city and focus entirely on work without the comfort-zone pull of home. Result: Relocation is not a concern for me; the role and the team matter more than geography.',
 'Common HR question'),

('hr', 'why-should-we-hire', 3,
 'Why should we hire you over other candidates?',
 'Situation: Many candidates will have similar GPAs and coursework. Task: I need to show what sets me apart without putting others down. Action: What I bring is the intersection of three things: I have shipped production code during my internship, I have led a team project from design to deployment, and I actively contribute to open-source tooling in the testing space. Most candidates have one of these; I have all three, and I am hungry to do more. Result: I will add value from week one because I have already been through a real development cycle, and I treat every code review as a learning opportunity.',
 'Common HR question'),

-- ===================== BEHAVIOURAL (10) =====================

('behavioural', 'leadership', 2,
 'Describe a situation where you had to lead a team.',
 'Situation: In semester six our software engineering course required a four-person team to build and deploy a clinic appointment system in eight weeks. Nobody volunteered to lead. Task: I stepped up because the alternative was chaos. Action: I created a Notion board with weekly milestones, assigned modules based on each member''s strengths, and held fifteen-minute Monday syncs. When one member fell behind on the API, I pair-programmed with him over a weekend. Result: We were the only team that deployed to a live URL, and the professor featured our project in the next batch''s orientation.',
 'Classic behavioural'),

('behavioural', 'failure', 2,
 'Tell me about a time you failed.',
 'Situation: During a hackathon I tried to integrate a payment gateway I had never used. Task: I was responsible for the checkout flow and had 24 hours. Action: I spent 14 hours fighting the SDK instead of reading the full docs first. I kept trying quick fixes instead of stepping back. Result: The checkout did not work in the demo and we lost the prize. Lesson: I now spend the first hour reading docs end to end before writing any integration code. At my internship I applied this and integrated a third-party analytics SDK in a single afternoon.',
 'Classic behavioural'),

('behavioural', 'initiative', 2,
 'Give an example of when you took initiative beyond your assigned work.',
 'Situation: During my internship the QA team manually tested API responses by copying curl commands from Slack. Task: Nobody asked me to fix this, but it was clearly a bottleneck. Action: I wrote a small Pytest suite that hit the staging API with the fifty most common requests and compared responses against JSON schemas. I added it to the CI pipeline over a weekend. Result: The QA lead said it cut their regression testing time from two hours to eight minutes, and the suite caught a breaking change the following week before it reached production.',
 'Classic behavioural'),

('behavioural', 'adaptability', 2,
 'Describe a time when you had to learn something new quickly.',
 'Situation: Three weeks into my internship the team decided to migrate the frontend from JavaScript to TypeScript. Task: I had never used TypeScript and had two sprints of feature work already assigned. Action: I spent the first weekend going through the TypeScript handbook, then converted my own module first as a learning exercise. I documented the five most common migration patterns I discovered and shared them with the team. Result: My module was the first fully converted, and the patterns doc became the team''s migration guide.',
 'Classic behavioural'),

('behavioural', 'time-management', 1,
 'How do you prioritise when you have multiple deadlines?',
 'Situation: In my sixth semester I had a DBMS assignment, a machine-learning lab submission, and a hackathon all in the same week. Task: I needed to deliver all three without sacrificing quality. Action: I listed every deliverable, estimated hours, and sorted by deadline. I did the DBMS assignment first because it was due Monday and was the smallest. Then I blocked Tuesday and Wednesday for the ML lab. Thursday and Friday went to the hackathon. I used Pomodoro intervals and turned off notifications. Result: I submitted all three on time. The ML lab scored 95 and our hackathon team placed second.',
 'Classic behavioural'),

('behavioural', 'communication', 2,
 'Describe a situation where you had to explain a technical concept to a non-technical person.',
 'Situation: My internship manager, who was a product manager with a business background, asked me why the dashboard was slow. Task: I needed to explain a database indexing problem without jargon. Action: I compared the database to a library: without an index it reads every book to find one title; with an index it goes straight to the shelf. I showed a before-and-after query time on screen — 4.2 seconds versus 80 milliseconds. Result: She immediately approved the indexing task in the next sprint and started using the library analogy with clients.',
 'Classic behavioural'),

('behavioural', 'ethical-dilemma', 3,
 'Have you ever faced an ethical dilemma at work or in a project?',
 'Situation: During my internship I found that the analytics dashboard silently dropped rows where a nullable field was missing, which inflated the conversion rate by about 12%. Task: The inflated number was already in a board presentation. Reporting it meant embarrassing my manager. Action: I documented the bug with exact queries, showed the correct versus inflated numbers, and told my manager privately before anyone else. I also prepared a one-line fix. Result: He appreciated the heads-up, corrected the board deck, and deployed the fix the same day. I learned that honesty early is always cheaper than a cover-up later.',
 'Classic behavioural'),

('behavioural', 'receiving-feedback', 1,
 'Tell me about a time you received critical feedback.',
 'Situation: During my first code review at the internship, the senior developer left 23 comments on a 200-line PR. Task: I felt defensive but knew I was there to learn. Action: I went through every comment, grouped them into categories — naming conventions, error handling, test coverage — and fixed them one by one. I also asked him to pair-review my next PR live so I could learn his thought process. Result: My second PR had only four comments. By the end of the internship he trusted me to review other interns'' code.',
 'Classic behavioural'),

('behavioural', 'ambiguity', 3,
 'Describe a project where the requirements were unclear.',
 'Situation: A client at my internship company asked for a "smart search" feature but could not define what "smart" meant. Task: I needed to build something useful without a clear spec. Action: I interviewed three end-users, identified that they mostly searched by date range and client name, and built a two-filter search with a keyword fallback. I shipped an MVP in four days and gathered feedback. The users asked for one more filter (status), which I added in a day. Result: The client signed off on the feature in one iteration instead of the usual three, because the MVP forced concrete feedback instead of abstract requirements.',
 'Classic behavioural'),

('behavioural', 'mentoring', 3,
 'Have you ever mentored someone? What was the experience like?',
 'Situation: In my final year, a second-year student from my college''s coding club asked me to help him prepare for his first hackathon. Task: He knew basic Python but had never built a web app. Action: Over two weeks I ran four one-hour sessions: HTTP basics, Flask routing, connecting to SQLite, and deploying on Render. I gave him small exercises between sessions and reviewed his code on GitHub. Result: His team built a working event-registration app at the hackathon and placed third. He now mentors first-years in the same club. The experience taught me that teaching forces you to understand fundamentals at a deeper level.',
 'Classic behavioural'),

-- ===================== TECHNICAL (12) =====================

('technical', 'oop-concepts', 1,
 'Explain the four pillars of Object-Oriented Programming with examples.',
 'Encapsulation: bundling data and methods that operate on it into a class and restricting direct access. Example: a BankAccount class with a private balance field and a public deposit() method that validates the amount before updating.

Abstraction: hiding complex implementation behind a simple interface. Example: a DatabaseConnection abstract class with a connect() method — MySQL and Postgres subclasses implement it differently, but the caller only sees connect().

Inheritance: a child class acquiring fields and methods from a parent. Example: Vehicle is the base; Car extends it and adds seatCount. Car inherits startEngine() without rewriting it.

Polymorphism: the same method name behaving differently depending on the object. Example: a Shape interface with area(). Circle returns π·r², Rectangle returns l·w. A function that takes Shape can call area() on either without knowing the concrete type.',
 'Core CS concept'),

('technical', 'dbms-normalisation', 1,
 'What is database normalisation? Explain up to 3NF with an example.',
 'Normalisation removes redundancy and update anomalies by decomposing tables.

1NF: every column holds atomic values, no repeating groups. A table storing "skills: Java,Python" in one column violates 1NF. Fix: a separate skills table with one row per skill.

2NF: already in 1NF and every non-key column depends on the entire primary key, not just part of it. A table (student_id, course_id, student_name, grade) has student_name depending only on student_id. Fix: separate Students(student_id, student_name) from Enrolments(student_id, course_id, grade).

3NF: already in 2NF and no non-key column depends on another non-key column (no transitive dependency). A table (employee_id, department_id, department_name) has department_name depending on department_id, not on employee_id. Fix: Employees(employee_id, department_id) and Departments(department_id, department_name).',
 'Core DBMS concept'),

('technical', 'arrays-strings', 1,
 'Given an array of integers, find two numbers that add up to a given target. Explain your approach and its time complexity.',
 'Approach: use a hash set. Walk the array once. For each element x, check if (target − x) is already in the set. If yes, return the pair. If no, add x to the set.

Why this works: by the time we reach the second element of a valid pair, the first is already in the set.

Time complexity: O(n) — one pass, and set lookup is O(1) on average.
Space complexity: O(n) — the set may hold up to n elements.

Code sketch (Python):
def two_sum(nums, target):
    seen = set()
    for x in nums:
        complement = target - x
        if complement in seen:
            return (complement, x)
        seen.add(x)
    return None

Edge cases: duplicates (the set handles them naturally), negative numbers (arithmetic still works), empty array (returns None).',
 'LeetCode easy / classic'),

('technical', 'rest-api-design', 2,
 'Design a REST API for a simple to-do list application. What endpoints would you create?',
 'Resources: User, Task.

Endpoints:
POST   /users          — register
POST   /auth/login     — returns a JWT
GET    /tasks           — list the authenticated user''s tasks (supports ?status=pending&page=1)
POST   /tasks           — create a task (body: { title, description?, due_date? })
GET    /tasks/:id       — get one task (404 if not the user''s)
PATCH  /tasks/:id       — update fields (title, description, due_date, status)
DELETE /tasks/:id       — soft-delete or hard-delete

Design decisions:
1. Authentication via Bearer JWT in the Authorization header.
2. Pagination with page and per_page query params, response includes total_count.
3. Status codes: 201 on create, 200 on update, 204 on delete, 422 for validation errors.
4. Error envelope: { "error": { "code": "not_found", "message": "..." } }.
5. Versioning: prefix all routes with /v1.
6. Rate limiting: 429 with Retry-After header.',
 'System design basics'),

('technical', 'sql-queries', 2,
 'Write a SQL query to find the second-highest salary from an Employees table.',
 'Approach 1 — DISTINCT + LIMIT/OFFSET:
SELECT DISTINCT salary
FROM employees
ORDER BY salary DESC
LIMIT 1 OFFSET 1;

Approach 2 — subquery:
SELECT MAX(salary)
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);

Approach 3 — DENSE_RANK window function:
SELECT salary
FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk
  FROM employees
) ranked
WHERE rnk = 2;

DENSE_RANK is preferred when there can be ties and you want all employees at the second-highest level. The subquery approach handles NULLs correctly because MAX ignores them. LIMIT/OFFSET is simplest but returns only one row even if multiple employees share that salary.',
 'Common SQL interview question'),

('technical', 'os-process-thread', 2,
 'What is the difference between a process and a thread?',
 'A process is an independent program in execution with its own address space, file descriptors, and resources. A thread is a lightweight unit of execution within a process that shares the process''s memory and resources.

Key differences:
1. Memory: processes have separate address spaces; threads share heap and global memory within the same process.
2. Creation cost: forking a process is expensive (copy page tables); creating a thread is cheap (just a new stack and register set).
3. Communication: inter-process communication (pipes, sockets, shared memory + synchronisation) is complex; threads communicate through shared variables (but need locks/mutexes to avoid races).
4. Fault isolation: a crash in one process does not affect others; a crash in one thread can take down the entire process.
5. Context switch: switching between threads of the same process is faster because the TLB and cache stay warm.

Real-world example: a web server like Nginx uses multiple processes for fault isolation; each process uses threads (or async I/O) for concurrency within a single core.',
 'Core OS concept'),

('technical', 'linked-list', 1,
 'How do you detect a cycle in a linked list?',
 'Use Floyd''s Tortoise and Hare algorithm.

Algorithm:
1. Start two pointers at the head: slow moves one node per step, fast moves two.
2. If fast reaches null, there is no cycle.
3. If fast equals slow at any point, there is a cycle.

Why it works: if there is a cycle of length C, once both pointers are inside the cycle, the gap between them shrinks by 1 each step (fast gains 1 on slow), so they must meet within C steps.

Time complexity: O(n) — each pointer traverses at most n + C nodes.
Space complexity: O(1) — only two pointers, no extra data structure.

To find the start of the cycle: once slow and fast meet, reset slow to head. Move both one step at a time. They meet at the cycle start. Proof relies on the fact that the distance from head to cycle start equals the distance from meeting point to cycle start (modulo cycle length).',
 'Classic DSA question'),

('technical', 'system-design-url', 3,
 'Design a URL shortener like bit.ly. Walk through the high-level architecture.',
 'Requirements: shorten a URL, redirect on the short code, track click counts, handle millions of reads per second.

Short code generation: Base62 encode an auto-incrementing ID (or a distributed ID like Snowflake). 7 characters gives 62^7 ≈ 3.5 trillion unique codes.

Storage: a Postgres or DynamoDB table — (short_code PK, original_url, user_id, created_at, click_count). Reads vastly exceed writes, so this is a read-heavy system.

Read path: 1. Client hits GET /:code → 2. Check Redis cache (code → URL). Cache hit → 301 redirect. Cache miss → query DB, populate cache, redirect. 3. Increment click count asynchronously (Kafka or an in-memory buffer flushed periodically).

Write path: POST /shorten with the URL → generate code → insert into DB → return short URL.

Scaling: Redis handles the hot read path. Multiple app servers behind a load balancer. Database sharding by code prefix if needed. CDN for static assets.

Reliability: short codes are immutable once created, so caching is safe. TTL on cache entries for deleted URLs. Rate-limit the create endpoint to prevent abuse.',
 'Classic system design'),

('technical', 'git-workflow', 1,
 'What is the difference between git merge and git rebase?',
 'Both integrate changes from one branch into another, but they produce different histories.

git merge: creates a new merge commit with two parents, preserving the full branching history. The feature branch''s commits remain as they were.
Pros: non-destructive, easy to understand.
Cons: creates extra merge commits, history can look cluttered.

git rebase: replays the feature branch''s commits on top of the target branch, rewriting their hashes. The result is a linear history.
Pros: clean, linear commit log.
Cons: rewrites history (dangerous on shared branches), can cause conflicts commit by commit.

Rule of thumb: rebase your local/feature branch onto main before merging; never rebase a branch others are working on. Many teams use "rebase + merge --no-ff" to get a linear history with a clear merge point.',
 'Version control basics'),

('technical', 'concurrency', 3,
 'Explain deadlock. What are the four necessary conditions and how can you prevent it?',
 'A deadlock occurs when two or more threads are each waiting for a resource held by another, forming a circular wait, so none can proceed.

Four necessary conditions (Coffman conditions):
1. Mutual exclusion — at least one resource is non-sharable.
2. Hold and wait — a thread holds one resource while waiting for another.
3. No preemption — resources cannot be forcibly taken from a thread.
4. Circular wait — a cycle exists in the wait-for graph.

All four must hold simultaneously for a deadlock.

Prevention strategies (break any one condition):
1. Break mutual exclusion: use lock-free data structures (CAS operations). Not always possible.
2. Break hold and wait: require a thread to request all resources at once (all-or-nothing).
3. Allow preemption: if a thread cannot get a resource, release everything it holds and retry.
4. Break circular wait: impose a global ordering on resources; always acquire locks in the same order.

Detection: maintain a wait-for graph and periodically check for cycles (databases do this). Recovery: kill one thread in the cycle and release its resources.',
 'Core OS/concurrency concept'),

('technical', 'networking-tcp-udp', 1,
 'What is the difference between TCP and UDP?',
 'TCP (Transmission Control Protocol):
- Connection-oriented: requires a three-way handshake (SYN, SYN-ACK, ACK).
- Reliable: guarantees delivery, ordering, and error checking. Retransmits lost packets.
- Flow and congestion control: adjusts sending rate.
- Use cases: web browsing (HTTP), email (SMTP), file transfer (FTP), SSH.

UDP (User Datagram Protocol):
- Connectionless: no handshake, just send.
- Unreliable: no delivery guarantee, no ordering, no retransmission.
- Lightweight: smaller header (8 bytes vs TCP''s 20+), lower latency.
- Use cases: video streaming, online gaming, DNS lookups, VoIP.

When to choose:
- Need reliability and ordering → TCP.
- Need speed and can tolerate some loss → UDP.
- Modern protocols like QUIC (used by HTTP/3) build reliability on top of UDP to get the best of both worlds.',
 'Core networking concept'),

('technical', 'react-state', 2,
 'Explain the difference between useState and useEffect in React.',
 'useState: declares a piece of reactive state inside a function component. Returns [currentValue, setterFunction]. When the setter is called with a new value, React re-renders the component.
Example: const [count, setCount] = useState(0);

useEffect: runs side effects after the component renders. Takes a callback and an optional dependency array.
- No deps array: runs after every render.
- Empty array []: runs once after mount (like componentDidMount).
- [dep1, dep2]: runs after mount and whenever dep1 or dep2 changes.
The callback can return a cleanup function that runs before the next effect or on unmount.

Example:
useEffect(() => {
  const id = setInterval(() => setCount(c => c + 1), 1000);
  return () => clearInterval(id);  // cleanup
}, []);

Key distinction: useState is for data the component owns and renders. useEffect is for synchronising with external systems (APIs, timers, DOM mutations, subscriptions). A common mistake is using useEffect to derive state — that should be a plain variable or useMemo instead.',
 'React fundamentals');

-- ===================== APTITUDE (8) =====================

insert into app.questions (round_type, topic, difficulty, prompt, reference_answer, source) values

('aptitude', 'percentages', 1,
 'A shopkeeper marks an item 30% above cost price and then offers a 10% discount. What is the profit percentage?',
 'Let cost price = 100.
Marked price = 100 + 30% of 100 = 130.
Selling price after 10% discount = 130 − 10% of 130 = 130 − 13 = 117.
Profit = 117 − 100 = 17.
Profit percentage = (17 / 100) × 100 = 17%.

Key concept: successive percentage changes are not additive. 30% markup minus 10% discount ≠ 20% profit, because the discount is calculated on the marked price, not the cost price.',
 'Quantitative aptitude'),

('aptitude', 'probability', 2,
 'Two dice are thrown simultaneously. What is the probability that the sum is 7?',
 'Total outcomes when two dice are thrown = 6 × 6 = 36.
Favourable outcomes for sum = 7: (1,6), (2,5), (3,4), (4,3), (5,2), (6,1) → 6 outcomes.
Probability = 6/36 = 1/6 ≈ 0.1667 or about 16.67%.

Approach: list all pairs (a, b) where a + b = 7 and both a, b are in {1, 2, 3, 4, 5, 6}. For any target sum S between 2 and 12, the number of favourable outcomes is 6 − |S − 7|.',
 'Quantitative aptitude'),

('aptitude', 'time-work', 2,
 'A can complete a task in 12 days, B can complete it in 18 days. If they work together, how many days will it take?',
 'A''s rate = 1/12 of the task per day.
B''s rate = 1/18 of the task per day.
Combined rate = 1/12 + 1/18 = 3/36 + 2/36 = 5/36 of the task per day.
Time to complete = 36/5 = 7.2 days.

Shortcut formula for two workers: (A × B) / (A + B) = (12 × 18) / (12 + 18) = 216 / 30 = 7.2 days.',
 'Quantitative aptitude'),

('aptitude', 'logical-reasoning', 1,
 'Complete the series: 2, 6, 12, 20, 30, ?',
 'Look at the differences between consecutive terms:
6 − 2 = 4, 12 − 6 = 6, 20 − 12 = 8, 30 − 20 = 10.
The differences form an arithmetic sequence: 4, 6, 8, 10, so the next difference is 12.
Next term = 30 + 12 = 42.

Alternative: the n-th term is n × (n + 1). For n = 1: 1×2 = 2, n = 2: 2×3 = 6, ..., n = 6: 6×7 = 42.',
 'Logical reasoning'),

('aptitude', 'speed-distance', 2,
 'A train 150 metres long passes a pole in 15 seconds. How long will it take to pass a platform 300 metres long?',
 'Speed of train = distance / time = 150 / 15 = 10 m/s.
To pass the platform, the train must cover its own length plus the platform length = 150 + 300 = 450 metres.
Time = 450 / 10 = 45 seconds.

Key insight: passing a pole means the entire train crosses a single point, so distance = train length. Passing a platform means the front enters and the tail clears, so distance = train length + platform length.',
 'Quantitative aptitude'),

('aptitude', 'permutations', 2,
 'In how many ways can the letters of the word "BANANA" be arranged?',
 'BANANA has 6 letters: B(1), A(3), N(2).
Total arrangements = 6! / (3! × 2! × 1!) = 720 / (6 × 2 × 1) = 720 / 12 = 60.

Formula for permutations with repetition: n! / (n1! × n2! × ... × nk!) where n is the total number of items and n1, n2, ..., nk are the frequencies of each distinct item.',
 'Quantitative aptitude'),

('aptitude', 'profit-loss', 1,
 'A man buys an article for ₹800 and sells it at a loss of 15%. What is the selling price?',
 'Cost price = ₹800.
Loss = 15% of 800 = 0.15 × 800 = ₹120.
Selling price = Cost price − Loss = 800 − 120 = ₹680.

Shortcut: Selling price = Cost price × (1 − loss%) = 800 × 0.85 = ₹680.',
 'Quantitative aptitude'),

('aptitude', 'data-interpretation', 3,
 'A company''s revenue was ₹40 lakh in 2021, ₹52 lakh in 2022, and ₹46.8 lakh in 2023. What is the average annual growth rate over this period?',
 'Growth in 2022: (52 − 40) / 40 × 100 = 30%.
Growth in 2023: (46.8 − 52) / 52 × 100 = −10% (a decline).

Average annual growth rate (simple average): (30 + (−10)) / 2 = 10%.

CAGR (Compound Annual Growth Rate): (46.8 / 40)^(1/2) − 1 = (1.17)^0.5 − 1 ≈ 1.0817 − 1 = 8.17%.

The CAGR is more accurate for comparing with other investments because it accounts for compounding. The simple average overstates growth when there is volatility.',
 'Data interpretation');
