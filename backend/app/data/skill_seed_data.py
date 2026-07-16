"""
Skill seed data.

Provenance
----------
These entries are drawn from Microsoft's open-source
`SkillsExtractorCognitiveSearch` dataset (MIT-licensed, archived repo):
https://github.com/microsoft/SkillsExtractorCognitiveSearch/blob/master/data/skill_patterns.jsonl

That file contains ~2,100 spaCy EntityRuler patterns covering technical
and business skills. This module curates a representative subset
(~180 entries spanning languages, frameworks, databases, cloud
platforms, DevOps tooling, data science, and soft/business skills)
rather than reproducing the full file verbatim — chosen for signal
density in a resume-screening context over raw completeness. The
`category` field was inferred during curation; the upstream dataset
does not include categorization.

This is a starting point, not a ceiling: `Skill` is a normal database
table (see `app/models/skill.py`), so it can be extended via the admin
API (a natural Milestone 8+ feature) without any code changes here.
"""

SKILL_SEED_DATA: list[dict[str, str]] = [
    # --- Programming Languages ---
    {"name": "Python", "category": "Programming Language"},
    {"name": "Java", "category": "Programming Language"},
    {"name": "JavaScript", "category": "Programming Language"},
    {"name": "TypeScript", "category": "Programming Language"},
    {"name": "C++", "category": "Programming Language"},
    {"name": "C", "category": "Programming Language"},
    {"name": "C#", "category": "Programming Language"},
    {"name": "Go", "category": "Programming Language"},
    {"name": "Rust", "category": "Programming Language"},
    {"name": "Ruby", "category": "Programming Language"},
    {"name": "PHP", "category": "Programming Language"},
    {"name": "Swift", "category": "Programming Language"},
    {"name": "Kotlin", "category": "Programming Language"},
    {"name": "Scala", "category": "Programming Language"},
    {"name": "R", "category": "Programming Language"},
    {"name": "SQL", "category": "Programming Language"},
    {"name": "Bash", "category": "Programming Language"},
    {"name": "Elixir", "category": "Programming Language"},
    {"name": "Erlang", "category": "Programming Language"},
    {"name": "Haskell", "category": "Programming Language"},
    {"name": "Clojure", "category": "Programming Language"},
    {"name": "Dart", "category": "Programming Language"},
    {"name": "Fortran", "category": "Programming Language"},
    {"name": "COBOL", "category": "Programming Language"},
    {"name": "MATLAB", "category": "Programming Language"},

    # --- Frontend Frameworks / Libraries ---
    {"name": "React", "category": "Frontend Framework"},
    {"name": "Angular", "category": "Frontend Framework"},
    {"name": "Vue.js", "category": "Frontend Framework"},
    {"name": "AngularJS", "category": "Frontend Framework"},
    {"name": "Svelte", "category": "Frontend Framework"},
    {"name": "Ember.js", "category": "Frontend Framework"},
    {"name": "Backbone.js", "category": "Frontend Framework"},
    {"name": "jQuery", "category": "Frontend Framework"},
    {"name": "Next.js", "category": "Frontend Framework"},
    {"name": "Gatsby", "category": "Frontend Framework"},
    {"name": "Redux", "category": "Frontend Framework"},
    {"name": "Tailwind CSS", "category": "Frontend Framework"},
    {"name": "Bootstrap", "category": "Frontend Framework"},
    {"name": "D3.js", "category": "Frontend Framework"},
    {"name": "Three.js", "category": "Frontend Framework"},

    # --- Backend Frameworks ---
    {"name": "Django", "category": "Backend Framework"},
    {"name": "Flask", "category": "Backend Framework"},
    {"name": "FastAPI", "category": "Backend Framework"},
    {"name": "Express.js", "category": "Backend Framework"},
    {"name": "Spring", "category": "Backend Framework"},
    {"name": "Ruby on Rails", "category": "Backend Framework"},
    {"name": "Laravel", "category": "Backend Framework"},
    {"name": "ASP.NET", "category": "Backend Framework"},
    {"name": "NestJS", "category": "Backend Framework"},
    {"name": "Gin", "category": "Backend Framework"},
    {"name": "Django REST Framework", "category": "Backend Framework"},

    # --- Databases ---
    {"name": "PostgreSQL", "category": "Database"},
    {"name": "MySQL", "category": "Database"},
    {"name": "MongoDB", "category": "Database"},
    {"name": "Redis", "category": "Database"},
    {"name": "SQLite", "category": "Database"},
    {"name": "Cassandra", "category": "Database"},
    {"name": "DynamoDB", "category": "Database"},
    {"name": "Elasticsearch", "category": "Database"},
    {"name": "Oracle Database", "category": "Database"},
    {"name": "Microsoft SQL Server", "category": "Database"},
    {"name": "Neo4j", "category": "Database"},
    {"name": "CouchDB", "category": "Database"},
    {"name": "MariaDB", "category": "Database"},
    {"name": "InfluxDB", "category": "Database"},

    # --- Cloud Platforms ---
    {"name": "AWS", "category": "Cloud Platform"},
    {"name": "Amazon EC2", "category": "Cloud Platform"},
    {"name": "Amazon S3", "category": "Cloud Platform"},
    {"name": "AWS Lambda", "category": "Cloud Platform"},
    {"name": "Amazon RDS", "category": "Cloud Platform"},
    {"name": "Azure", "category": "Cloud Platform"},
    {"name": "Google Cloud Platform", "category": "Cloud Platform"},
    {"name": "Google Kubernetes Engine", "category": "Cloud Platform"},
    {"name": "Google Cloud Functions", "category": "Cloud Platform"},
    {"name": "Heroku", "category": "Cloud Platform"},
    {"name": "DigitalOcean", "category": "Cloud Platform"},
    {"name": "Firebase", "category": "Cloud Platform"},
    {"name": "Cloudflare", "category": "Cloud Platform"},

    # --- DevOps / Infrastructure ---
    {"name": "Docker", "category": "DevOps"},
    {"name": "Kubernetes", "category": "DevOps"},
    {"name": "Docker Compose", "category": "DevOps"},
    {"name": "Terraform", "category": "DevOps"},
    {"name": "Ansible", "category": "DevOps"},
    {"name": "Jenkins", "category": "DevOps"},
    {"name": "GitLab CI", "category": "DevOps"},
    {"name": "GitHub Actions", "category": "DevOps"},
    {"name": "CircleCI", "category": "DevOps"},
    {"name": "Prometheus", "category": "DevOps"},
    {"name": "Grafana", "category": "DevOps"},
    {"name": "Nginx", "category": "DevOps"},
    {"name": "Apache HTTP Server", "category": "DevOps"},
    {"name": "Chef", "category": "DevOps"},
    {"name": "Puppet", "category": "DevOps"},
    {"name": "Vagrant", "category": "DevOps"},
    {"name": "Datadog", "category": "DevOps"},

    # --- Data Science / ML / AI ---
    {"name": "Machine Learning", "category": "Data Science"},
    {"name": "Deep Learning", "category": "Data Science"},
    {"name": "Natural Language Processing", "category": "Data Science"},
    {"name": "Computer Vision", "category": "Data Science"},
    {"name": "TensorFlow", "category": "Data Science"},
    {"name": "PyTorch", "category": "Data Science"},
    {"name": "scikit-learn", "category": "Data Science"},
    {"name": "Keras", "category": "Data Science"},
    {"name": "Pandas", "category": "Data Science"},
    {"name": "NumPy", "category": "Data Science"},
    {"name": "Data Visualization", "category": "Data Science"},
    {"name": "Data Mining", "category": "Data Science"},
    {"name": "Data Analysis", "category": "Data Science"},
    {"name": "Feature Engineering", "category": "Data Science"},
    {"name": "Neural Networks", "category": "Data Science"},
    {"name": "Reinforcement Learning", "category": "Data Science"},
    {"name": "Apache Spark", "category": "Data Science"},
    {"name": "Apache Airflow", "category": "Data Science"},
    {"name": "Apache Kafka", "category": "Data Science"},
    {"name": "Hadoop", "category": "Data Science"},
    {"name": "Big Data", "category": "Data Science"},
    {"name": "ETL", "category": "Data Science"},
    {"name": "Data Warehousing", "category": "Data Science"},
    {"name": "Business Intelligence", "category": "Data Science"},
    {"name": "Tableau", "category": "Data Science"},
    {"name": "Power BI", "category": "Data Science"},
    {"name": "A/B Testing", "category": "Data Science"},
    {"name": "Statistical Analysis", "category": "Data Science"},

    # --- Testing / QA ---
    {"name": "Unit Testing", "category": "Testing"},
    {"name": "Integration Testing", "category": "Testing"},
    {"name": "pytest", "category": "Testing"},
    {"name": "Jest", "category": "Testing"},
    {"name": "Selenium", "category": "Testing"},
    {"name": "Cypress", "category": "Testing"},
    {"name": "JUnit", "category": "Testing"},
    {"name": "Test-Driven Development", "category": "Testing"},
    {"name": "Cucumber", "category": "Testing"},
    {"name": "Postman", "category": "Testing"},

    # --- Tools / Version Control ---
    {"name": "Git", "category": "Tools"},
    {"name": "GitHub", "category": "Tools"},
    {"name": "GitLab", "category": "Tools"},
    {"name": "Bitbucket", "category": "Tools"},
    {"name": "Jira", "category": "Tools"},
    {"name": "Confluence", "category": "Tools"},
    {"name": "Slack", "category": "Tools"},
    {"name": "VS Code", "category": "Tools"},
    {"name": "IntelliJ IDEA", "category": "Tools"},
    {"name": "Figma", "category": "Tools"},

    # --- Architecture / Concepts ---
    {"name": "REST API", "category": "Architecture"},
    {"name": "GraphQL", "category": "Architecture"},
    {"name": "Microservices", "category": "Architecture"},
    {"name": "Distributed Systems", "category": "Architecture"},
    {"name": "System Design", "category": "Architecture"},
    {"name": "Design Patterns", "category": "Architecture"},
    {"name": "Object-Oriented Programming", "category": "Architecture"},
    {"name": "Functional Programming", "category": "Architecture"},
    {"name": "Data Structures", "category": "Architecture"},
    {"name": "Algorithms", "category": "Architecture"},
    {"name": "Concurrency", "category": "Architecture"},
    {"name": "gRPC", "category": "Architecture"},
    {"name": "Message Queues", "category": "Architecture"},
    {"name": "Event-Driven Architecture", "category": "Architecture"},
    {"name": "Domain-Driven Design", "category": "Architecture"},

    # --- Security ---
    {"name": "Authentication", "category": "Security"},
    {"name": "OAuth", "category": "Security"},
    {"name": "Encryption", "category": "Security"},
    {"name": "Cryptography", "category": "Security"},
    {"name": "Computer Security", "category": "Security"},
    {"name": "Penetration Testing", "category": "Security"},

    # --- Methodology / Project Management ---
    {"name": "Agile", "category": "Methodology"},
    {"name": "Scrum", "category": "Methodology"},
    {"name": "Kanban", "category": "Methodology"},
    {"name": "Project Management", "category": "Methodology"},
    {"name": "Continuous Integration", "category": "Methodology"},
    {"name": "Continuous Deployment", "category": "Methodology"},
    {"name": "Code Review", "category": "Methodology"},

    # --- Business / Soft Skills ---
    {"name": "Communication", "category": "Soft Skill"},
    {"name": "Leadership", "category": "Soft Skill"},
    {"name": "Collaboration", "category": "Soft Skill"},
    {"name": "Problem Solving", "category": "Soft Skill"},
    {"name": "Business Administration", "category": "Business"},
    {"name": "Accounting", "category": "Business"},
    {"name": "Finance", "category": "Business"},
    {"name": "Marketing", "category": "Business"},
    {"name": "Customer Relationship Management", "category": "Business"},
    {"name": "Email Marketing", "category": "Business"},
    {"name": "Google Analytics", "category": "Business"},
]
