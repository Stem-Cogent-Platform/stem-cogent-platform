from app.ingestion.base_collector import BaseCollector, CollectionJob, FetchedPayload
from app.ingestion.http import ApprovedHttpFetcher


class APICollector(BaseCollector):
    def __init__(self, *args, http_fetcher: ApprovedHttpFetcher, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._http = http_fetcher

    async def fetch(self, job: CollectionJob) -> FetchedPayload:
        response = await self._http.fetch(job.source_url)
        return FetchedPayload(
            body=response.body,
            content_type=response.content_type,
            extension="json",
            source_url=response.final_url,
        )
