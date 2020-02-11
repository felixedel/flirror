# flirror


# Raspberry configuration

To hide the mouse cursor, install unclutter via

```
sudo apt install unclutter
```

and add the following line to `/home/pi/.config/lxsession/LXDE-pi/autostart`

```
@unclutter -display :0 -noevents -grab
```
