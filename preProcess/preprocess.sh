while read p; do
    if grep -Fxq "$p" ./targets/completed.out
    then
        continue
    else
python3 mastFits.py "$p" >> ./targets/completed.out
fi
done < ./targets/objects.csv