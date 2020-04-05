


while true
do
  ./run.sh
  gpio mode 7 out
  gpio write 7 off
  sleep 0.1
done
