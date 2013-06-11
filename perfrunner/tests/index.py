from perfrunner.tests import PerfTest
from perfrunner.tests.viewgen import ViewGen


class IndexTest(PerfTest):

    def __init__(self, *args):
        super(IndexTest, self).__init__(*args)

        views_settings = self.test_config.get_index_settings()
        if views_settings.disabled_updates:
            options = {'updateMinChanges': 0, 'replicaUpdateMinChanges': 0}
        else:
            options = None

        self.ddocs = ViewGen().generate_ddocs(views_settings.views, options)

    def _build_index(self):
        for target in self.target_iterator:
            for ddoc_name, ddoc in self.ddocs.iteritems():
                self.rest.create_ddoc(target.node, target.bucket,
                                      ddoc_name, ddoc)
                for view_name in ddoc['views']:
                    self.rest.query_view(target.node, target.bucket,
                                         ddoc_name, view_name,
                                         params={'limit': 10})

            self.monitor.monitor_task(target, 'indexer')

    def _compact_index(self):
        for target in self.target_iterator:
            for ddoc_name in self.ddocs:
                self.rest.trigger_index_compaction(target.node, ddoc_name,
                                                   target.bucket)
            self.monitor.monitor_task(target, 'view_compaction')


class InitialIndexTest(IndexTest):

    def run(self):
        self._run_load_phase()
        self._compact_bucket()

        self.reporter.start()
        self._build_index()
        self.reporter.finish('Initial index')


class IncrementalIndexTest(IndexTest):

    def run(self):
        self._run_load_phase()
        self._compact_bucket()

        self._build_index()

        self._run_access_phase()
        self._compact_bucket()

        self.reporter.start()
        self._build_index()
        self.reporter.finish('Incremental index')