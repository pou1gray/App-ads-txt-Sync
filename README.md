# App-ads Sync

A simple tool that allows you to sync your `app-ads.txt` in just a few clicks if you are using **GitHub Pages** to host your `app-ads.txt`.

Yes, doing it manually is very easy, but I decided to automate this task a little, so maybe you will find it useful too.

I use this program to sync the `app-ads.txt` file from [CAS.AI](https://github.com/cleveradssolutions).

---

## How to Use

1. **Specify the source `app-ads.txt`**  
   For CAS.AI, this is the raw link to their `app-ads.txt` in their repository:  
   `https://raw.githubusercontent.com/cleveradssolutions/App-ads.txt/refs/heads/main/app-ads.txt`  

   ![Enter source URL](images/screenshot00.png)

2. **Specify the location of your `app-ads.txt` in your local repository**  
   Example:  
   `C:\Projects\pou1gray.github.io\app-ads.txt`  

   ![Enter app-ads.txt path](images/screenshot01.png)

3. **After success just commit and push to git**  
   ![Success!](images/screenshot02.png)
   ![Push and commit](images/screenshot03.png)

---

The source URL and local path you enter are saved in a `config.json` file.  
In the future, you can simply run the program and then do `git commit` and `git push` - no need to enter the paths again.