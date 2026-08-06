# Architecture

## Entity-Relationship Diagram

```mermaid
erDiagram
  USERS ||--o{ JOBS : posts
  USERS ||--o{ RESUMES : uploads
  JOBS ||--o{ APPLICATIONS : receives
  RESUMES ||--o{ APPLICATIONS : submitted_in
  APPLICATIONS ||--|| SCORES : scored_by
  SKILLS ||--o{ RESUME_SKILLS : tagged_on
  RESUMES ||--o{ RESUME_SKILLS : has
  SKILLS ||--o{ JOB_SKILLS : required_in
  JOBS ||--o{ JOB_SKILLS : requires

  USERS {
    uuid id PK
    string email
    enum role
  }
  JOBS {
    uuid id PK
    uuid recruiter_id FK
    string title
  }
  RESUMES {
    uuid id PK
    uuid candidate_id FK
    text parsed_text
    float extracted_years_experience
    enum extracted_education_level
    json embedding
  }
  APPLICATIONS {
    uuid id PK
    uuid job_id FK
    uuid resume_id FK
    enum status
  }
  SCORES {
    uuid id PK
    uuid application_id FK
    float overall_score
    json explanation
  }
  SKILLS {
    uuid id PK
    string name
    string category
  }
```

## AI Pipeline (Milestones 4-6)

```
Resume upload (PDF/DOCX)
  -> text extraction (pdfplumber / python-docx)
  -> text cleaning
  -> skill extraction (spaCy PhraseMatcher gazetteer)
  -> experience extraction (regex)
  -> education extraction (keyword matching)
  -> embedding generation (all-MiniLM-L6-v2, stored on Resume.embedding)

Recruiter search:
  job description text
  -> embedding
  -> FAISS IndexFlatIP assembled from all stored resume embeddings
  -> ranked results by cosine similarity
```

See [docs/MILESTONES.md](../MILESTONES.md) for the full narrative and every
real bug hit along the way.
