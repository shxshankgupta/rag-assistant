from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import CurrentUser, enforce_api_rate_limit, get_document_service
from app.schemas.documents import DocumentListResponse, DocumentResponse
from app.services.document_response_builder import document_to_response
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_api_rate_limit)],
)
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """
    Upload a PDF document and process it inline.
    The response returns once extraction, chunking, embedding, and indexing succeed.
    """
    doc = await doc_svc.upload_document(file, current_user)
    return document_to_response(doc)


@router.get("/", response_model=DocumentListResponse, dependencies=[Depends(enforce_api_rate_limit)])
async def list_documents(
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """List all documents belonging to the authenticated user."""
    return await doc_svc.list_documents(current_user.id)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(enforce_api_rate_limit)],
)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Get a single document's metadata and processing stage."""
    doc = await doc_svc.get_document(document_id, current_user.id)
    return document_to_response(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_api_rate_limit)],
)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> None:
    """Delete a document and remove its vectors from the index."""
    await doc_svc.delete_document(document_id, current_user.id)
