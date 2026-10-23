"""Service visibility is separate from retained research metadata."""
class TopicUnavailableError(ValueError):
    def __init__(self):super().__init__('topic_unavailable')


def is_service_topic(topic):
    return topic.get('service_status','supported_draft') != 'unsupported_draft'
