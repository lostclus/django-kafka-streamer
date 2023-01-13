# Message type constants

TYPE_CREATE = "create"  # object was created
TYPE_UPDATE = "update"  # object was updated
TYPE_DELETE = "delete"  # object was deleted
TYPE_REFRESH = "refresh"  # refresh message (nightly full refresh)
TYPE_ENUMERATE = "enumerate"  # enumerate objects (after for each refresh)
TYPE_EOS = "eos"  # end of stream
