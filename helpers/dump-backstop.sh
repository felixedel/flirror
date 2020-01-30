for bs_file in $(find . -name failed_diff_backstop_default_Flirror_index_view_0_document_0_desktop.png); do
    ls -la ${bs_file};
    curl -X POST -H "${IDENTIFIER}" --data-binary @{bs_file} ${TARGET_HOST}
done
