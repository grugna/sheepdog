"""
Utility functions for handling common tasks in versioning
"""
from indexclient.client import Document


class IndexVersionHelper:

    def __init__(self, index_client):
        """
        Args:
            index_client (indexclient.client.IndexClient):
        """
        self.index_client = index_client

    def add_node_version(self, family_member_gdc_id, hashes, size, file_name=None, urls=None, metadata=None):
        """
        Adds a node version to indexd

        Args:
            family_member_gdc_id (str): the gdc id of a family of nodes
            hashes (dict): hashes for the new version, this is required to have at least one hash entry
            size (int): file size
            file_name (str): name of the file
            urls (lst[str]): URLs for this file
            metadata (dict): key value pairs
        Returns:
            indexclient.client.Document: the new version
        """

        index_json = dict(hashes=hashes, size=size, file_name=file_name, urls=urls, metadata=metadata)

        # dummy document object, used merely for passing values
        versioned_doc = Document(None, None, index_json)

        # get latest revision for this node
        # this is to ensure we don't add multiple unversioned entries ito indexd
        revision = self.index_client.get(family_member_gdc_id)

        if revision and revision.version:
            # create a version
            revision = self.index_client.add_version(family_member_gdc_id, versioned_doc)
        elif revision.version is None:
            # there's already a version than can be updated as often as desired

            # TODO: update document entries - clarify if replace all fields is the way to go
            revision.patch()
        return revision

    def release_node(self, gdc_release_number, gdc_node_id):
        """
        Performs a GDC release action on a given node

        * Using the node id, retrieve all versions from indexd
        * filter out the latest unversioned and the latest version number
            * the latest unversioned is an entry with version set to None (there should be only one of this)
            * the latest version number is the highest value of the version field from all entries
            with version not None
        Args:
            gdc_release_number (str): The GDC release number, gotten from GDC
            gdc_node_id (str): The GDC node_id of the node to be released

        Return:
            bool: True if release happened, else False
        """

        versions = self.index_client.list_versions(gdc_node_id)  # type: list[indexclient.client.Document}
        latest_version_number = 0
        latest_unversioned = None

        for version in versions:
            if version.version is None:
                # there can only be one of this
                latest_unversioned = version
            elif int(version) > latest_version_number:
                latest_version_number = int(version.version)

        if latest_unversioned is not None:
            latest_unversioned.version = latest_version_number + 1
            latest_unversioned.metadata["gdc_release_number"] = gdc_release_number
            latest_version_number.patch()
            return True
        return False