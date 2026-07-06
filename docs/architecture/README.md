# Architecture

## Entity-Relationship Diagram

GitHub renders Mermaid diagrams natively in markdown -- this is the same
schema shown interactively during the build (see Milestone 2 in
[docs/MILESTONES.md](../MILESTONES.md)).

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
    string hashed_password
    enum role
    string full_name
    bool is_active
    timestamp created_at
  }
  JOBS {
    uuid id PK
    uuid recruiter_id FK
    string title
    text description
    int min_experience_years
    enum status
    timestamp created_at
  }
  RESUMES {
    uuid id PK
    uuid candidate_id FK
    string original_filename
    string storage_path
    enum file_type
    text parsed_text
    timestamp uploaded_at
  }
  APPLICATIONS {
    uuid id PK
    uuid job_id FK
    uuid resume_id FK
    enum status
    timestamp applied_at
  }
  SCORES {
    uuid id PK
    uuid application_id FK
    float skills_match_score
    float experience_match_score
    float education_match_score
    float semantic_similarity_score
    float ats_score
    float overall_score
    json explanation
  }
  SKILLS {
    uuid id PK
    string name
    string category
  }
  RESUME_SKILLS {
    uuid resume_id FK
    uuid skill_id FK
  }
  JOB_SKILLS {
    uuid job_id FK
    uuid skill_id FK
    bool is_required
  }
```

## System Architecture

```
Client (React/TS)
      |  HTTPS
      v
FastAPI (versioned REST API, /api/v1)
      |
      +--> PostgreSQL   (users, jobs, resumes, scores -- system of record)
      +--> Redis        (cache + Celery broker)
      +--> Celery workers (async: parsing, embedding generation, scoring)
```

Layered backend structure -- each layer depends only on the layer below it:

```
app/
|-- api/        HTTP layer: routers, request/response handling only
|-- schemas/    Pydantic request/response contracts
|-- services/   Business logic -- framework-agnostic
|-- models/     SQLAlchemy ORM models (persistence layer)
|-- ai/         NLP/ML pipeline (parsing, embeddings, scoring)
|-- workers/    Celery task definitions
|-- core/       Config, logging, security -- cross-cutting concerns
`-- db/         Database session/engine management
```

## Design decisions log

See [docs/MILESTONES.md](../MILESTONES.md) for the full narrative of *why*
each decision was made, including the real debugging history -- config
path resolution, port collisions, cross-dialect UUID/JSON handling, and
Alembic's custom-type import limitation. That file is the one worth
rereading before an interview; this one is the quick-reference diagram.
