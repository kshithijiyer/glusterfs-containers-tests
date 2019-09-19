from openshiftstoragelibs.baseclass import BaseClass
from openshiftstoragelibs import heketi_ops
from openshiftstoragelibs import heketi_version
from openshiftstoragelibs import openshift_ops


class TestHeketiServerStateExamineGluster(BaseClass):

    def setUp(self):
        self.node = self.ocp_master_node[0]
        version = heketi_version.get_heketi_version(self.heketi_client_node)
        if version < '8.0.0-7':
            self.skipTest("heketi-client package %s does not support server "
                          "state examine gluster" % version.v_str)

    def test_volume_inconsistencies(self):
        # Examine Gluster cluster and Heketi that there is no inconsistencies
        out = heketi_ops.heketi_examine_gluster(
            self.heketi_client_node, self.heketi_server_url)
        if ("heketi volume list matches with volume list of all nodes"
                not in out['report']):
            self.skipTest(
                "heketi and Gluster are inconsistent to each other")

        # create volume
        vol = heketi_ops.heketi_volume_create(
            self.heketi_client_node, self.heketi_server_url, 1, json=True)
        self.addCleanup(
            heketi_ops.heketi_volume_delete, self.heketi_client_node,
            self.heketi_server_url, vol['id'])

        # delete volume from gluster cluster directly
        openshift_ops.cmd_run_on_gluster_pod_or_node(
            self.node,
            "gluster vol stop %s force --mode=script" % vol['name'])
        openshift_ops.cmd_run_on_gluster_pod_or_node(
            self.node,
            "gluster vol delete %s --mode=script" % vol['name'])

        # verify that heketi is reporting inconsistencies
        out = heketi_ops.heketi_examine_gluster(
            self.heketi_client_node, self.heketi_server_url)
        self.assertNotIn(
            "heketi volume list matches with volume list of all nodes",
            out['report'])

    def test_compare_real_vol_count_with_db_check_info(self):
        """Validate volumes using heketi db check"""

        # Create volume
        vol = heketi_ops.heketi_volume_create(
            self.heketi_client_node, self.heketi_server_url, 1, json=True)
        self.addCleanup(
            heketi_ops.heketi_volume_delete, self.heketi_client_node,
            self.heketi_server_url, vol['id'])

        # Check heketi db
        db_result = heketi_ops.heketi_db_check(
            self.heketi_client_node, self.heketi_server_url)
        vol_count = db_result["volumes"]["total"]
        vol_list = heketi_ops.heketi_volume_list(
            self.heketi_client_node, self.heketi_server_url, json=True)
        count = len(vol_list["volumes"])
        self.assertEqual(
            count, vol_count, "Volume count doesn't match expected"
            " result %s, actual  result is %s" % (
                count, vol_count))
