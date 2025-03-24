from import_export import resources
from .models import Book

class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'publication_year', 'genre', 'isbn')
        export_order = ('id', 'title', 'author', 'publication_year', 'genre', 'isbn')
