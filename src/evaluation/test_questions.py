# ── Test questions with ground truth ──────────────────────────────────────

TEST_QUESTIONS = [
    {
        "question": "What is an Aggregate in Domain-Driven Design and why is it important?",
        "intent": "concept",
        "ground_truth": "An Aggregate is a cluster of domain objects grouped around an Aggregate Root that ensures consistency boundaries. It is important because it enforces transactional consistency and encapsulates business rules within a bounded context.",
        "expected_sources": ["ddd-glossary", "aggregate-design-rules-vernon"],
    },
    {
        "question": "How do I implement Constructor-based Autowiring instead of Field-based Autowiring in Spring?",
        "intent": "procedure",
        "ground_truth": "Replace @Autowired field injection with constructor injection by declaring dependencies as constructor parameters. Spring automatically injects them. Use final fields and a single constructor for cleaner, testable code.",
        "expected_sources": ["antipatterns-spring-jpa"],
    },
    {
        "question": "Show me a code example of a side effect in a method that violates Clean Code principles.",
        "intent": "example",
        "ground_truth": "A method that modifies global state, writes to a file, or changes an input parameter as a hidden side effect violates the Clean Code principle of doing one thing. The method name should reflect all its actions.",
        "expected_sources": ["2G20nqeHAn8"],
    },
    {
        "question": "What is the difference between Entity and Value Object in DDD?",
        "intent": "comparison",
        "ground_truth": "An Entity has a unique identity that persists across time, while a Value Object is defined by its attributes and has no identity. Entities are mutable and tracked by ID; Value Objects are immutable and compared by value.",
        "expected_sources": ["ddd-glossary"],
    },
    {
        "question": "Why should I use UUID instead of Long for Entity IDs in Spring JPA?",
        "intent": "rule",
        "ground_truth": "UUIDs can be generated client-side without database interaction, enabling proper equals/hashCode before persistence. Long IDs from sequences create problems with entity identity in collections before the entity is saved.",
        "expected_sources": ["antipatterns-spring-jpa"],
    },
    {
        "question": "Why should I learn about Clean Code rules and what are the key takeaways?",
        "intent": "summary",
        "ground_truth": "Clean Code improves readability, maintainability, and reduces bugs. Key takeaways include meaningful naming, small functions that do one thing, avoiding side effects, and writing code that reads like well-written prose.",
        "expected_sources": ["2G20nqeHAn8"],
    },
]