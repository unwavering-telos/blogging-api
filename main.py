from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Session, col, create_engine, or_, select
from datetime import datetime
from contextlib import asynccontextmanager


class Post(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str
    content: str
    category: str
    tags: str
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)


class PostSchema(BaseModel):
    title: str
    content: str
    category: str
    tags: list[str]


class PostSchemaResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    tags: list[str]
    createdAt: datetime
    updatedAt: datetime


DATA_BASE_URL = "sqlite:///blog.db"
engine = create_engine(DATA_BASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    print("アプリを終了します")


app = FastAPI(lifespan=lifespan)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def post_response(post: Post) -> PostSchemaResponse:
    return PostSchemaResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        category=post.category,
        tags=post.tags.split(",") if post.tags else [],
        createdAt=post.createdAt,
        updatedAt=post.updatedAt,
    )


# 作成
@app.post("/posts", response_model=PostSchemaResponse, status_code=201)
def create_post(post_data: PostSchema, session: SessionDep):
    post = Post(
        title=post_data.title,
        content=post_data.content,
        category=post_data.category,
        tags=",".join(post_data.tags),
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post_response(post)


# 一覧取得
@app.get("/posts", response_model=list[PostSchemaResponse])
def get_posts(session: SessionDep, term: str | None = None):
    query = select(Post)
    if term:
        query = query.where(
            or_(
                col(Post.title).contains(term),
                col(Post.content).contains(term),
                col(Post.category).contains(term),
            )
        )
    posts = session.exec(query).all()
    return [post_response(n) for n in posts]


# 一件取得
@app.get("/posts/{post_id}", response_model=PostSchemaResponse)
def get_post(post_id: int, session: SessionDep):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post_response(post)


# 更新
@app.put("/posts/{post_id}", response_model=PostSchemaResponse)
def update_post(post_id: int, post_data: PostSchema, session: SessionDep):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.title = post_data.title
    post.content = post_data.content
    post.category = post_data.category
    post.tags = ",".join(post_data.tags)
    post.updatedAt = datetime.now()

    session.commit()
    session.refresh(post)
    return post_response(post)


# 削除
@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, session: SessionDep):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    session.delete(post)
    session.commit()


@app.get("/")
def root():
    return {"message": "hello"}
