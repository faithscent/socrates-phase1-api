#!/bin/bash
# Pulls today's IV/skew snapshot for every proxy symbol, then pushes
# everything (breadth + IV) to Supabase in one go.
#
# Run this regularly — daily if you want tight resolution, weekly at
# minimum alongside your Socrates report update — to build up IV history.
# The "IV rank" shown on dashboard.html is a real percentile computed from
# whatever iv_snapshots history has actually accumulated (see
# v_iv_rank_latest in supabase_schema.sql): it stays labeled "building
# history" until at least 4 readings exist for a symbol, and only gets
# more trustworthy the more often this runs. There is no way to backfill
# past IV — Yahoo Finance doesn't expose historical option chains, so a
# day this doesn't run is a day of IV history you don't get back.
#
# Safe to run more than once on the same day — iv_snapshot.py skips a
# symbol it already has today's row for, and push_to_supabase.py upserts,
# so re-running never duplicates anything.
set -e
echo "Fetching today's IV snapshot..."
python "/Users/Ruthie/Downloads/socrates_data main/socrates_data_main_dashboard/iv_snapshot.py"
echo ""
echo "Pushing to Supabase (breadth + IV)..."
python "/Users/Ruthie/Downloads/n8n_pipeline_1/push_to_supabase.py"
