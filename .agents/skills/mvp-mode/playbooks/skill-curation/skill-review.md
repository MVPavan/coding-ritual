# Skill review: comparing skills

Use it to decide a merge, upgrade or rebuild of one of our skills, or when
`placing.md` step 4 finds two skills in one sub-stage. Run the `harness-skill-compare`
skill. It writes `harness_lifecycle/registry/reviews/<yyyy-mm-dd>-skill-<our-skill>.md` with
the set, the components with `file:line`, the presence matrix, the
differences with the stronger mechanism, and a verdict. The verdict is a
recommendation; rulings follow from the playbook's one path (`../skill-curation.md`).
