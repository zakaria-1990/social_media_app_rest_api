from fastapi import Response, status, HTTPException, Depends, APIRouter
from .. import schemas, models, oauth2
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db


router = APIRouter(
    prefix='/posts',
    tags=['posts'],
)


@router.get('/', status_code=status.HTTP_200_OK, response_model=list[schemas.PostOut])
async def get_posts(db: Session = Depends(get_db), limit: int = 10, skip: int = 0, search: str | None = ""):
    posts = db.query(models.Post, func.count(models.Vote.post_id).label("votes")).\
        join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)\
        .group_by(models.Post.id).\
        filter(models.Post.title.contains(search)).limit(limit).offset(skip).all()
    return posts


@router.post('/', status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
async def create_posts(post: schemas.PostCreate, db: Session = Depends(get_db),
                       current_user: int = Depends(oauth2.get_current_user)):
    new_post = models.Post(owner_id=current_user.id, **post.dict())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.get('/{id}', response_model=schemas.PostOut)
async def get_post(id: int, response: Response, db: Session = Depends(get_db)):
    post = db.query(models.Post, func.count(models.Vote.post_id).label("votes"))\
        .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)\
        .group_by(models.Post.id)\
        .filter(models.Post.id == id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id number {id} not found')
    return post


@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(id: int, db: Session = Depends(get_db),
                      current_user: int = Depends(oauth2.get_current_user)):
    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id number {id} not found')
    if post.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Not authorized to perfom requested action')
    post_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put('/{id}', response_model=schemas.Post)
async def update_post(id: int, updated_post: schemas.PostCreate, db: Session = Depends(get_db),
                      current_user: int = Depends(oauth2.get_current_user)):
    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id number {id} not found')
    post_query.update(updated_post.dict(), synchronize_session=False)
    db.commit()
    return post_query.first()
