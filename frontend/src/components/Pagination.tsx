interface PaginationProps {
  offset: number;
  limit: number;
  totalResults: number;
  onOffsetChange: (offset: number) => void;
}

function calculateTotalPages(total: number, limit: number): number {
  return Math.ceil(total / limit);
}

function Pagination({
  totalResults = 0,
  offset = 0,
  limit = 10,
  onOffsetChange,
}: PaginationProps) {
  const currentPage = offset / limit + 1;
  const totalPages = calculateTotalPages(totalResults, limit);

  const firstPage = currentPage === 1;
  const lastPage = currentPage === totalPages;

  const handlePreviousPage = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    if (!firstPage) {
      onOffsetChange(offset - limit);
    }
  };

  const handleNextPage = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    if (!lastPage) {
      onOffsetChange(offset + limit);
    }
  };

  return (
    <nav
      className="page-navigation context-add-url"
    >
      <a
        style={{
          pointerEvents: firstPage ? "none" : undefined,
        }}
        href="#"
        className="pagination-page"
        onClick={handlePreviousPage}
      >
        Previous
      </a>
      <span
        style={{
          pointerEvents: 'none',
        }}
        className="pagination-page"
      >
        Page {currentPage} / {totalPages}
      </span>
      <a
        style={{
          userSelect: "none",
          pointerEvents: lastPage ? "none" : undefined,
        }}
        href="#"
        className="pagination-page"
        onClick={handleNextPage}
      >
        Next
      </a>
    </nav>
  );
}

export default Pagination;
