# Copyright 2009-2025 Noviat
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import models


def uninstall_hook(env):
    lang = env.user.lang
    env.cr.execute(
        f"""
        DROP INDEX IF EXISTS account_account__name_index;

        ALTER TABLE account_account
        ALTER COLUMN name TYPE JSONB
        USING jsonb_build_object('{lang}', name);

        CREATE INDEX account_account__name_index
        ON account_account
        USING gin ((jsonb_path_query_array(name, '$.*'::jsonpath)::text) gin_trgm_ops);
        """
    )
