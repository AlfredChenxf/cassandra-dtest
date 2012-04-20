from dtest import Tester
from assertions import *
from tools import *

import os, sys, time, tools
from uuid import UUID
from ccmlib.cluster import Cluster

cql_version="3.0.0-beta1"

class TestCQL(Tester):

    @since('1.1')
    def static_cf_test(self):
        """ Test non-composite static CF syntax """
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        # Create
        cursor.execute("""
            CREATE TABLE users (
                userid uuid PRIMARY KEY,
                firstname text,
                lastname text,
                age int
            );
        """)

        # Inserts
        cursor.execute("INSERT INTO users (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, Frodo, Baggins, 32)")
        cursor.execute("UPDATE users SET firstname = Samwise, lastname = Gamgee, age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479")

        # Queries
        cursor.execute("SELECT firstname, lastname FROM users WHERE userid = 550e8400-e29b-41d4-a716-446655440000");
        res = cursor.fetchall()
        assert res == [[ 'Frodo', 'Baggins' ]], res

        cursor.execute("SELECT * FROM users WHERE userid = 550e8400-e29b-41d4-a716-446655440000");
        res = cursor.fetchall()
        assert res == [[ UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins' ]], res

        cursor.execute("SELECT * FROM users");
        res = cursor.fetchall()
        assert res == [
            [ UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 33, 'Samwise', 'Gamgee' ],
            [ UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins' ],
        ], res

        # Test batch inserts
        cursor.execute("""
            BEGIN BATCH
                INSERT INTO users (userid, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 36)
                UPDATE users SET age = 37 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
                DELETE firstname, lastname FROM users WHERE userid = 550e8400-e29b-41d4-a716-446655440000
                DELETE firstname, lastname FROM users WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
            APPLY BATCH
        """)

        cursor.execute("SELECT * FROM users")
        res = cursor.fetchall()
        assert res == [
            [ UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 37, None, None ],
            [ UUID('550e8400-e29b-41d4-a716-446655440000'), 36, None, None ],
        ], res

    @since('1.1')
    def dynamic_cf_test(self):
        """ Test non-composite dynamic CF syntax """
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE clicks (
                userid uuid,
                url text,
                time bigint,
                PRIMARY KEY (userid, url)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        cursor.execute("INSERT INTO clicks (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://foo.bar', 42)")
        cursor.execute("INSERT INTO clicks (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://foo-2.bar', 24)")
        cursor.execute("INSERT INTO clicks (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://bar.bar', 128)")
        cursor.execute("UPDATE clicks SET time = 24 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 and url = 'http://bar.foo'")
        cursor.execute("UPDATE clicks SET time = 12 WHERE userid IN (f47ac10b-58cc-4372-a567-0e02b2c3d479, 550e8400-e29b-41d4-a716-446655440000) and url = 'http://foo-3'")

        # Queries
        cursor.execute("SELECT url, time FROM clicks WHERE userid = 550e8400-e29b-41d4-a716-446655440000")
        res = cursor.fetchall()
        assert res == [[ 'http://bar.bar', 128 ], [ 'http://foo-2.bar', 24 ], [ 'http://foo-3', 12 ], [ 'http://foo.bar', 42 ]], res

        cursor.execute("SELECT * FROM clicks WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479")
        res = cursor.fetchall()
        assert res == [
            [ UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 'http://bar.foo', 24 ],
            [ UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 'http://foo-3', 12 ]
        ], res

        cursor.execute("SELECT time FROM clicks")
        res = cursor.fetchall()
        # Result from 'f47ac10b-58cc-4372-a567-0e02b2c3d479' are first
        assert res == [[24], [12], [128], [24], [12], [42]], res

    @since('1.1')
    def dense_cf_test(self):
        """ Test composite 'dense' CF syntax """
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE connections (
                userid uuid,
                ip text,
                port int,
                time bigint,
                PRIMARY KEY (userid, ip, port)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        cursor.execute("INSERT INTO connections (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.1', 80, 42)")
        cursor.execute("INSERT INTO connections (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.2', 80, 24)")
        cursor.execute("INSERT INTO connections (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.2', 90, 42)")
        cursor.execute("UPDATE connections SET time = 24 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.2' AND port = 80")

        # Queries
        cursor.execute("SELECT ip, port, time FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000")
        res = cursor.fetchall()
        assert res == [[ '192.168.0.1', 80, 42 ], [ '192.168.0.2', 80, 24 ], [ '192.168.0.2', 90, 42 ]], res

        cursor.execute("SELECT ip, port, time FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip >= '192.168.0.2'")
        res = cursor.fetchall()
        assert res == [[ '192.168.0.2', 80, 24 ], [ '192.168.0.2', 90, 42 ]], res

        cursor.execute("SELECT ip, port, time FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip = '192.168.0.2'")
        res = cursor.fetchall()
        assert res == [[ '192.168.0.2', 80, 24 ], [ '192.168.0.2', 90, 42 ]], res

        cursor.execute("SELECT ip, port, time FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip > '192.168.0.2'")
        res = cursor.fetchall()
        assert res == [], res

        # Deletion
        cursor.execute("DELETE time FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND ip = '192.168.0.2' AND port = 80")
        cursor.execute("SELECT * FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000")
        res = cursor.fetchall()
        assert len(res) == 2, res

        cursor.execute("DELETE FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000")
        cursor.execute("SELECT * FROM connections WHERE userid = 550e8400-e29b-41d4-a716-446655440000")
        res = cursor.fetchall()
        assert len(res) == 0, res

    @since('1.1')
    def sparse_cf_test(self):
        """ Test composite 'sparse' CF syntax """
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE timeline (
                userid uuid,
                posted_month int,
                posted_day int,
                body text,
                posted_by text,
                PRIMARY KEY (userid, posted_month, posted_day)
            );
        """)

        # Inserts
        cursor.execute("INSERT INTO timeline (userid, posted_month, posted_day, body, posted_by) VALUES (550e8400-e29b-41d4-a716-446655440000, 1, 12, 'Something else', 'Frodo Baggins')")
        cursor.execute("INSERT INTO timeline (userid, posted_month, posted_day, body, posted_by) VALUES (550e8400-e29b-41d4-a716-446655440000, 1, 24, 'Something something', 'Frodo Baggins')")
        cursor.execute("UPDATE timeline SET body = 'Yo Froddo', posted_by = 'Samwise Gamgee' WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND posted_month = 1 AND posted_day = 3")
        cursor.execute("UPDATE timeline SET body = 'Yet one more message' WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 and posted_day = 30")

        # Queries
        cursor.execute("SELECT body, posted_by FROM timeline WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 AND posted_day = 24")
        res = cursor.fetchall()
        assert res == [[ 'Something something', 'Frodo Baggins' ]], res

        cursor.execute("SELECT posted_day, body, posted_by FROM timeline WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 AND posted_day > 12")
        res = cursor.fetchall()
        assert res == [
            [ 24, 'Something something', 'Frodo Baggins' ],
            [ 30, 'Yet one more message', None ]
        ], res

        cursor.execute("SELECT posted_day, body, posted_by FROM timeline WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1")
        res = cursor.fetchall()
        assert res == [
            [ 12, 'Something else', 'Frodo Baggins' ],
            [ 24, 'Something something', 'Frodo Baggins' ],
            [ 30, 'Yet one more message', None ]
        ], res

    @since('1.1')
    def create_invalid_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        assert_invalid(cursor, "CREATE TABLE test ()")
        assert_invalid(cursor, "CREATE TABLE test (key text PRIMARY KEY)")
        assert_invalid(cursor, "CREATE TABLE test (c1 text, c2 text, c3 text)")
        assert_invalid(cursor, "CREATE TABLE test (key1 text PRIMARY KEY, key2 text PRIMARY KEY)")

        assert_invalid(cursor, "CREATE TABLE test (key text PRIMARY KEY, key int)")
        assert_invalid(cursor, "CREATE TABLE test (key text PRIMARY KEY, c int, c text)")

        assert_invalid(cursor, "CREATE TABLE test (key text PRIMARY KEY, c int, d text) WITH COMPACT STORAGE")
        assert_invalid(cursor, "CREATE TABLE test (key text, key2 text, c int, d text, PRIMARY KEY (key, key2)) WITH COMPACT STORAGE")

    @since('1.1')
    def limit_ranges_test(self):
        cluster = self.cluster
        # We don't yet support paging for RP
        cluster.set_partitioner("org.apache.cassandra.dht.ByteOrderedPartitioner")

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE clicks (
                userid int,
                url text,
                time bigint,
                PRIMARY KEY (userid, url)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for id in xrange(0, 100):
            for tld in [ 'com', 'org', 'net' ]:
                cursor.execute("INSERT INTO clicks (userid, url, time) VALUES (%i, 'http://foo.%s', 42)" % (id, tld))

        # Queries
        cursor.execute("SELECT * FROM clicks WHERE userid >= 2 LIMIT 1")
        res = cursor.fetchall()
        assert res == [[ 2, 'http://foo.com', 42 ]], res

        cursor.execute("SELECT * FROM clicks WHERE userid > 2 LIMIT 1")
        res = cursor.fetchall()
        assert res == [[ 3, 'http://foo.com', 42 ]], res

    @since('1.1')
    def limit_multiget_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE clicks (
                userid int,
                url text,
                time bigint,
                PRIMARY KEY (userid, url)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for id in xrange(0, 100):
            for tld in [ 'com', 'org', 'net' ]:
                cursor.execute("INSERT INTO clicks (userid, url, time) VALUES (%i, 'http://foo.%s', 42)" % (id, tld))

        # Queries
        # That that we do limit the output to 1 *and* that we respect query
        # order of keys (even though 48 is after 2)
        cursor.execute("SELECT * FROM clicks WHERE userid IN (48, 2) LIMIT 1")
        res = cursor.fetchall()
        assert res == [[ 48, 'http://foo.com', 42 ]], res

    @since('1.1')
    def limit_sparse_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE clicks (
                userid int,
                url text,
                day int,
                month text,
                year int,
                PRIMARY KEY (userid, url)
            );
        """)

        # Inserts
        for id in xrange(0, 100):
            for tld in [ 'com', 'org', 'net' ]:
                cursor.execute("INSERT INTO clicks (userid, url, day, month, year) VALUES (%i, 'http://foo.%s', 1, jan, 2012)" % (id, tld))

        # Queries
        # Check we do get as many rows as requested
        cursor.execute("SELECT * FROM clicks LIMIT 4")
        res = cursor.fetchall()
        assert len(res) == 4, res

    @since('1.1')
    def counters_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE clicks (
                userid int,
                url text,
                total counter,
                PRIMARY KEY (userid, url)
            ) WITH COMPACT STORAGE;
        """)

        cursor.execute("UPDATE clicks SET total = total + 1 WHERE userid = 1 AND url = 'http://foo.com'")
        cursor.execute("SELECT total FROM clicks WHERE userid = 1 AND url = 'http://foo.com'")
        res = cursor.fetchall()
        assert res == [[ 1 ]], res

        cursor.execute("UPDATE clicks SET total = total - 4 WHERE userid = 1 AND url = 'http://foo.com'")
        cursor.execute("SELECT total FROM clicks WHERE userid = 1 AND url = 'http://foo.com'")
        res = cursor.fetchall()
        assert res == [[ -3 ]], res

        cursor.execute("UPDATE clicks SET total = total+1 WHERE userid = 1 AND url = 'http://foo.com'")
        cursor.execute("SELECT total FROM clicks WHERE userid = 1 AND url = 'http://foo.com'")
        res = cursor.fetchall()
        assert res == [[ -2 ]], res

        cursor.execute("UPDATE clicks SET total = total -2 WHERE userid = 1 AND url = 'http://foo.com'")
        cursor.execute("SELECT total FROM clicks WHERE userid = 1 AND url = 'http://foo.com'")
        res = cursor.fetchall()
        assert res == [[ -4 ]], res

    @since('1.1')
    def indexed_with_eq_test(self):
        """ Check that you can query for an indexed column even with a key EQ clause """
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        # Create
        cursor.execute("""
            CREATE TABLE users (
                userid uuid PRIMARY KEY,
                firstname text,
                lastname text,
                age int
            );
        """)

        cursor.execute("CREATE INDEX byAge ON users(age)")

        # Inserts
        cursor.execute("INSERT INTO users (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, Frodo, Baggins, 32)")
        cursor.execute("UPDATE users SET firstname = Samwise, lastname = Gamgee, age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479")

        # Queries
        cursor.execute("SELECT firstname FROM users WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND age = 33");
        res = cursor.fetchall()
        assert res == [], res

        cursor.execute("SELECT firstname FROM users WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND age = 33");
        res = cursor.fetchall()
        assert res == [[ 'Samwise' ]], res

    @since('1.1')
    def select_key_in_test(self):
        """Query for KEY IN (...)"""
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        # Create
        cursor.execute("""
            CREATE TABLE users (
                userid uuid PRIMARY KEY,
                firstname text,
                lastname text,
                age int
            );
        """)

        # Inserts
        cursor.execute("""
                INSERT INTO users (userid, firstname, lastname, age)
                VALUES (550e8400-e29b-41d4-a716-446655440000, Frodo, Baggins, 32)
        """)
        cursor.execute("""
                INSERT INTO users (userid, firstname, lastname, age)
                VALUES (f47ac10b-58cc-4372-a567-0e02b2c3d479, Samwise, Gamgee, 33)
        """)

        # Select
        cursor.execute("""
                SELECT firstname, lastname FROM users
                WHERE userid IN (550e8400-e29b-41d4-a716-446655440000, f47ac10b-58cc-4372-a567-0e02b2c3d479)
        """);

        res = cursor.fetchall()
        assert len(res) == 2, res

    #@require('3785')
    def exclusive_slice_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE test (
                k int,
                c int,
                v int,
                PRIMARY KEY (k, c)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for x in range(0, 10):
            cursor.execute("INSERT INTO test (k, c, v) VALUES (0, %i, %i)" % (x, x))

        # Queries
        cursor.execute("SELECT v FROM test WHERE k = 0")
        res = cursor.fetchall()
        assert len(res) == 10, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c >= '' AND c <= ''")
        res = cursor.fetchall()
        assert len(res) == 10, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c > '' AND c < ''")
        res = cursor.fetchall()
        assert len(res) == 10, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c >= 2 AND c <= 6")
        res = cursor.fetchall()
        assert len(res) == 5 and res[0][0] == 2 and res[len(res) - 1][0] == 6, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c > 2 AND c <= 6")
        res = cursor.fetchall()
        assert len(res) == 4 and res[0][0] == 3 and res[len(res) - 1][0] == 6, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c >= 2 AND c < 6")
        res = cursor.fetchall()
        assert len(res) == 4 and res[0][0] == 2 and res[len(res) - 1][0] == 5, res

        cursor.execute("SELECT v FROM test WHERE k = 0 AND c > 2 AND c < 6")
        res = cursor.fetchall()
        assert len(res) == 3 and res[0][0] == 3 and res[len(res) - 1][0] == 5, res

    @since('1.1')
    def in_clause_wide_rows_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE test1 (
                k int,
                c int,
                v int,
                PRIMARY KEY (k, c)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for x in range(0, 10):
            cursor.execute("INSERT INTO test1 (k, c, v) VALUES (0, %i, %i)" % (x, x))

        cursor.execute("SELECT v FROM test1 WHERE k = 0 AND c IN (5, 2, 8)")
        res = cursor.fetchall()
        assert res == [[5], [2], [8]], res

        # composites
        cursor.execute("""
            CREATE TABLE test2 (
                k int,
                c1 int,
                c2 int,
                v int,
                PRIMARY KEY (k, c1, c2)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for x in range(0, 10):
            cursor.execute("INSERT INTO test2 (k, c1, c2, v) VALUES (0, 0, %i, %i)" % (x, x))

        # Check first we don't allow IN everywhere
        assert_invalid(cursor, "SELECT v FROM test2 WHERE k = 0 AND c1 IN (5, 2, 8) AND c2 = 3")

        cursor.execute("SELECT v FROM test2 WHERE k = 0 AND c1 = 0 AND c2 IN (5, 2, 8)")
        res = cursor.fetchall()
        assert res == [[5], [2], [8]], res

    @since('1.1')
    def order_by_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE test1 (
                k int,
                c int,
                v int,
                PRIMARY KEY (k, c)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        for x in range(0, 10):
            cursor.execute("INSERT INTO test1 (k, c, v) VALUES (0, %i, %i)" % (x, x))

        cursor.execute("SELECT v FROM test1 WHERE k = 0 ORDER BY c DESC")
        res = cursor.fetchall()
        assert res == [[x] for x in range(9, -1, -1)], res

        # composites
        cursor.execute("""
            CREATE TABLE test2 (
                k int,
                c1 int,
                c2 int,
                v int,
                PRIMARY KEY (k, c1, c2)
            );
        """)

        # Inserts
        for x in range(0, 4):
            for y in range(0, 2):
                cursor.execute("INSERT INTO test2 (k, c1, c2, v) VALUES (0, %i, %i, %i)" % (x, y, x * 2 + y))

        # Check first we don't always ORDER BY 
        assert_invalid(cursor, "SELECT v FROM test2 WHERE k = 0 ORDER BY c DESC")
        assert_invalid(cursor, "SELECT v FROM test2 WHERE k = 0 ORDER BY c2 DESC")
        assert_invalid(cursor, "SELECT v FROM test2 WHERE k = 0 ORDER BY k DESC")

        cursor.execute("SELECT v FROM test2 WHERE k = 0 ORDER BY c1 DESC")
        res = cursor.fetchall()
        assert res == [[x] for x in range(7, -1, -1)], res

        cursor.execute("SELECT v FROM test2 WHERE k = 0 ORDER BY c1")
        res = cursor.fetchall()
        assert res == [[x] for x in range(0, 8)], res

    #@require('#3708')
    def range_tombstones_test(self):
        cluster = self.cluster

        # Uses 3 nodes just to make sure RowMutation are correctly serialized
        cluster.populate(3).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE test1 (
                k int,
                c1 int,
                c2 int,
                v1 int,
                v2 int,
                PRIMARY KEY (k, c1, c2)
            );
        """)

        rows = 10
        col1 = 2
        col2 = 2
        cpr = col1 * col2
        for i in xrange(0, rows):
            for j in xrange(0, col1):
                for k in xrange(0, col2):
                    n = (i * cpr) + (j * col2) + k
                    cursor.execute("INSERT INTO test1 (k, c1, c2, v1, v2) VALUES (%d, %d, %d, %d, %d)" % (i, j, k, n, n))

        for i in xrange(0, rows):
            cursor.execute("SELECT v1, v2 FROM test1 where k = %d" % i)
            res = cursor.fetchall()
            assert res == [[x, x] for x in xrange(i * cpr, (i + 1) * cpr)], res

        for i in xrange(0, rows):
            cursor.execute("DELETE FROM test1 WHERE k = %d AND c1 = 0" % i)

        for i in xrange(0, rows):
            cursor.execute("SELECT v1, v2 FROM test1 WHERE k = %d" % i)
            res = cursor.fetchall()
            assert res == [[x, x] for x in xrange(i * cpr + col1, (i + 1) * cpr)], res

        cluster.flush()
        time.sleep(0.2)

        for i in xrange(0, rows):
            cursor.execute("SELECT v1, v2 FROM test1 WHERE k = %d" % i)
            res = cursor.fetchall()
            assert res == [[x, x] for x in xrange(i * cpr + col1, (i + 1) * cpr)], res

    @require('#3783')
    def null_support_test(self):
        cluster = self.cluster

        cluster.populate(1).start()
        node1 = cluster.nodelist()[0]
        time.sleep(0.2)

        cursor = self.cql_connection(node1, version=cql_version).cursor()
        self.create_ks(cursor, 'ks', 1)

        cursor.execute("""
            CREATE TABLE test1 (
                k int,
                c1 int,
                c2 int,
                c3 int,
                v int,
                PRIMARY KEY (k, c1, c2, c3)
            ) WITH COMPACT STORAGE;
        """)

        # Inserts
        cursor.execute("INSERT INTO test1 (k, c1, c2, c3, v) VALUES (0, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO test1 (k, c1, c2, c3, v) VALUES (0, 0, 0, 1, 1)")
        cursor.execute("INSERT INTO test1 (k, c1, c2, c3, v) VALUES (0, 0, 1, 0, 2)")
        cursor.execute("INSERT INTO test1 (k, c1, c2, c3, v) VALUES (0, 0, 1, 1, 3)")

        cursor.execute("INSERT INTO test1 (k, c1, c2, v) VALUES (0, 0, 0, 10)")
        cursor.execute("INSERT INTO test1 (k, c1, c2, c3, v) VALUES (0, 0, 1, null, 11)")

        #cursor.execute("SELECT v FROM test1 WHERE k = 0")
        #res = cursor.fetchall()
        #assert res == [[10], [0], [1], [11], [2], [3]], res

        #cursor.execute("SELECT v FROM test1 WHERE k = 0 AND c1 = 0 AND c2 = 0")
        #res = cursor.fetchall()
        #assert res == [[10], [0], [1]], res

        cursor.execute("SELECT v FROM test1 WHERE k = 0 AND c1 = 0 AND c2 = 0 AND c3 = null")
        res = cursor.fetchall()
        assert res == [[10]], res
